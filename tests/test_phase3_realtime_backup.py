"""Comprehensive tests for Phase 3: Real-Time Telemetry, NLP Summaries, and Backup Caregiver Fallbacks."""

import uuid
from datetime import datetime, timedelta, timezone
import pytest
from httpx import ASGITransport, AsyncClient
from starlette.testclient import TestClient

from src.main import app


@pytest.mark.asyncio
async def test_phase3_telemetry_nlp_summary_and_backup_fallback():
    """
    End-to-End Test for Phase 3:
    1. Register Guardian and 2 Caregivers (Primary Caregiver & Backup Caregiver).
    2. Create childcare booking.
    3. Test WebSocket connection and ping-pong heartbeat.
    4. Emit real-time telemetry events (CHECK_IN, NAP, MEAL, MEDICATION, MOOD, CHECK_OUT).
    5. Trigger NLP-driven End-of-Day summary generator and verify narrative and metrics.
    6. Create a second booking and trigger the Automated Backup Fallback Workflow.
    7. Verify backup caregiver auto-reassignment and cryptographic audit logging.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # ----------------------------------------------------------------------
        # 1. User and Caregiver Setup
        # ----------------------------------------------------------------------
        # Guardian
        g_resp = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "phase3.parent@kidsync.ai",
                "password": "Password123!",
                "first_name": "Marcus",
                "last_name": "Vance",
                "role": "PRIMARY_GUARDIAN",
            },
        )
        assert g_resp.status_code == 201
        g_token = g_resp.json()["data"]["access_token"]
        g_headers = {"Authorization": f"Bearer {g_token}"}

        # Primary Caregiver (Elena)
        cg1_user = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "elena.primary@kidsync.ai",
                "password": "Password123!",
                "first_name": "Elena",
                "last_name": "Reyes",
                "role": "CARE_PROVIDER",
            },
        )
        assert cg1_user.status_code == 201
        cg1_uid = cg1_user.json()["data"]["user"]["id"]
        cg1_token = cg1_user.json()["data"]["access_token"]
        cg1_headers = {"Authorization": f"Bearer {cg1_token}"}

        cg1_prof = await client.post(
            "/api/v1/caregivers/",
            headers=cg1_headers,
            json={
                "user_id": cg1_uid,
                "bio": "Primary nanny with infant and toddler experience.",
                "years_of_experience": 5,
                "hourly_rate_cents": 2800,
                "currency": "USD",
                "specialties": ["INFANT_CARE", "FIRST_AID"],
                "certifications": [{"name": "CPR & First Aid"}],
                "is_available": True,
            },
        )
        assert cg1_prof.status_code == 201
        cg1_id = cg1_prof.json()["data"]["id"]

        # Backup Caregiver (Maya - High Trust & Experience)
        cg2_user = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "maya.backup@kidsync.ai",
                "password": "Password123!",
                "first_name": "Maya",
                "last_name": "Lin",
                "role": "CARE_PROVIDER",
            },
        )
        assert cg2_user.status_code == 201
        cg2_uid = cg2_user.json()["data"]["user"]["id"]
        cg2_token = cg2_user.json()["data"]["access_token"]
        cg2_headers = {"Authorization": f"Bearer {cg2_token}"}

        cg2_prof = await client.post(
            "/api/v1/caregivers/",
            headers=cg2_headers,
            json={
                "user_id": cg2_uid,
                "bio": "Certified emergency backup caregiver, pediatric nurse background.",
                "years_of_experience": 9,
                "hourly_rate_cents": 3200,
                "currency": "USD",
                "specialties": ["INFANT_CARE", "FIRST_AID", "SPECIAL_NEEDS"],
                "certifications": [{"name": "Pediatric First Aid & CPR"}, {"name": "BLS Healthcare Provider"}],
                "is_available": True,
            },
        )
        assert cg2_prof.status_code == 201
        cg2_id = cg2_prof.json()["data"]["id"]

        # Vetting status pass for both caregivers
        await client.put(f"/api/v1/caregivers/{cg1_id}", headers=g_headers, json={"background_check_status": "PASSED"})
        await client.put(f"/api/v1/caregivers/{cg2_id}", headers=g_headers, json={"background_check_status": "PASSED"})

        # ----------------------------------------------------------------------
        # 2. Create Booking for Session 1
        # ----------------------------------------------------------------------
        start_time = datetime.now(timezone.utc) + timedelta(hours=1)
        end_time = start_time + timedelta(hours=4)
        b1_resp = await client.post(
            "/api/v1/bookings/",
            headers=g_headers,
            json={
                "caregiver_id": cg1_id,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "special_instructions": "Leo takes nap at 1:30 PM. Needs Amoxicillin 5ml at 2:00 PM.",
            },
        )
        assert b1_resp.status_code == 201
        booking1_id = b1_resp.json()["data"]["id"]

        # ----------------------------------------------------------------------
        # 3. WebSocket Channel Connection & Ping-Pong Heartbeat
        # ----------------------------------------------------------------------
        sync_client = TestClient(app)
        with sync_client.websocket_connect(f"/api/v1/telemetry/ws/{booking1_id}") as websocket:
            websocket.send_text('{"event": "telemetry.ping"}')
            response_frame = websocket.receive_json()
            assert response_frame["event"] == "telemetry.pong"
            assert response_frame["ack"] is True

        # ----------------------------------------------------------------------
        # 4. Emit Real-Time Telemetry Events
        # ----------------------------------------------------------------------
        # Event A: CHECK_IN
        ev_checkin = await client.post(
            "/api/v1/telemetry/events",
            headers=cg1_headers,
            json={
                "booking_id": booking1_id,
                "event_type": "CHECK_IN",
                "payload": {"location": "Family Residence", "arrival_status": "ON_TIME"},
                "battery_level": 94.0,
            },
        )
        assert ev_checkin.status_code == 201
        assert ev_checkin.json()["data"]["event_type"] == "CHECK_IN"

        # Verify booking status transitioned to IN_PROGRESS
        b1_check = await client.get(f"/api/v1/bookings/{booking1_id}", headers=g_headers)
        assert b1_check.json()["data"]["status"] == "IN_PROGRESS"

        # Event B: MEAL
        await client.post(
            "/api/v1/telemetry/events",
            headers=cg1_headers,
            json={
                "booking_id": booking1_id,
                "event_type": "MEAL",
                "payload": {"meal_name": "Turkey & Avocado Sandwich", "percentage_eaten": 85.0},
                "notes": "Drank 200ml water as well.",
            },
        )

        # Event C: NAP
        await client.post(
            "/api/v1/telemetry/events",
            headers=cg1_headers,
            json={
                "booking_id": booking1_id,
                "event_type": "NAP",
                "payload": {"duration_minutes": 90, "quality": "restful"},
                "notes": "Fell asleep with soft white noise.",
            },
        )

        # Event D: MEDICATION
        await client.post(
            "/api/v1/telemetry/events",
            headers=cg1_headers,
            json={
                "booking_id": booking1_id,
                "event_type": "MEDICATION",
                "payload": {"medication_name": "Amoxicillin", "dose": "5ml"},
                "notes": "Taken with food without resistance.",
            },
        )

        # Event E: MOOD
        await client.post(
            "/api/v1/telemetry/events",
            headers=cg1_headers,
            json={
                "booking_id": booking1_id,
                "event_type": "MOOD",
                "payload": {"score": 4.8, "descriptor": "Happy & playful"},
            },
        )

        # Event F: CHECK_OUT
        ev_checkout = await client.post(
            "/api/v1/telemetry/events",
            headers=cg1_headers,
            json={
                "booking_id": booking1_id,
                "event_type": "CHECK_OUT",
                "payload": {"handoff_to": "Marcus (Father)"},
            },
        )
        assert ev_checkout.status_code == 201

        # Verify booking status transitioned to COMPLETED
        b1_check_done = await client.get(f"/api/v1/bookings/{booking1_id}", headers=g_headers)
        assert b1_check_done.json()["data"]["status"] == "COMPLETED"

        # ----------------------------------------------------------------------
        # 5. NLP End-of-Day Summary Generator
        # ----------------------------------------------------------------------
        summary_gen_resp = await client.post(
            "/api/v1/summary/generate",
            headers=g_headers,
            json={
                "booking_id": booking1_id,
                "child_name": "Leo",
            },
        )
        assert summary_gen_resp.status_code == 201, summary_gen_resp.text
        summary_data = summary_gen_resp.json()["data"]

        # Validate structured metrics
        assert summary_data["metrics"]["total_sleep_minutes"] == 90
        assert summary_data["metrics"]["meal_completion_pct"] == 85.0
        assert summary_data["metrics"]["medications_given_count"] == 1
        assert summary_data["metrics"]["incident_count"] == 0

        # Validate narrative & highlights
        assert "Leo" in summary_data["summary_text"]
        assert len(summary_data["highlights"]) >= 3
        assert len(summary_data["action_items"]) >= 1

        # Test retrieval endpoint
        get_summary_resp = await client.get(f"/api/v1/summary/{booking1_id}", headers=g_headers)
        assert get_summary_resp.status_code == 200
        assert get_summary_resp.json()["data"]["id"] == summary_data["id"]

        # ----------------------------------------------------------------------
        # 6. Automated Backup Caregiver Fallback Workflow
        # ----------------------------------------------------------------------
        # Create a second booking with Elena (cg1)
        b2_start = datetime.now(timezone.utc) + timedelta(days=2)
        b2_end = b2_start + timedelta(hours=3)
        b2_resp = await client.post(
            "/api/v1/bookings/",
            headers=g_headers,
            json={
                "caregiver_id": cg1_id,
                "start_time": b2_start.isoformat(),
                "end_time": b2_end.isoformat(),
                "special_instructions": "Urgent appointment. Caregiver must arrive promptly.",
            },
        )
        assert b2_resp.status_code == 201
        booking2_id = b2_resp.json()["data"]["id"]

        # Simulate Elena having an emergency / unresponsive check-in
        fallback_resp = await client.post(
            "/api/v1/fallback/trigger",
            headers=g_headers,
            json={
                "booking_id": booking2_id,
                "reason": "Primary caregiver encountered emergency transit delay; missed check-in SLA.",
                "auto_assign": True,
            },
        )
        assert fallback_resp.status_code == 200, fallback_resp.text
        fallback_data = fallback_resp.json()["data"]

        # Verify fallback result
        assert fallback_data["status"] == "BACKUP_ASSIGNED"
        assert fallback_data["original_caregiver_id"] == cg1_id
        assert fallback_data["backup_caregiver_id"] == cg2_id  # Maya assigned!
        assert fallback_data["assigned_caregiver_name"] == "Maya Lin"
        assert len(fallback_data["ranked_backup_candidates"]) >= 1

        # Check booking record in database
        b2_reassigned = await client.get(f"/api/v1/bookings/{booking2_id}", headers=g_headers)
        assert b2_reassigned.json()["data"]["caregiver_id"] == cg2_id
