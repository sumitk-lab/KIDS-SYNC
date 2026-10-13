"""Comprehensive integration test suite for KidSync AI Phase 1 API endpoints."""

import os
import pytest
import pytest_asyncio
from datetime import datetime, timedelta, timezone
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.api.deps import get_db
from src.core.database import Base
from src.main import app



@pytest.mark.asyncio
async def test_health_check():
    """Test health probe endpoint."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "KidSync AI" in data["project"]


@pytest.mark.asyncio
async def test_full_phase1_workflow():
    """
    End-to-end integration test validating:
    1. Guardian user registration & authentication
    2. Caregiver user registration & profile creation
    3. Caregiver assignment to guardian family
    4. Childcare booking request with cost calculation
    5. Booking overlap deconfliction (HTTP 409 Conflict)
    6. Booking status transition to CONFIRMED
    7. Cryptographic audit chain HMAC-SHA256 verification (Zero tampering)
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Register Primary Guardian
        guardian_reg_resp = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "elena.guardian@kidsync.ai",
                "password": "SecurePassword123!",
                "first_name": "Elena",
                "last_name": "Vance",
                "phone": "+15550192831",
                "role": "PRIMARY_GUARDIAN",
            },
        )
        assert guardian_reg_resp.status_code == 201, guardian_reg_resp.text
        guardian_data = guardian_reg_resp.json()["data"]
        guardian_token = guardian_data["access_token"]
        guardian_id = guardian_data["user"]["id"]
        guardian_headers = {"Authorization": f"Bearer {guardian_token}"}

        # 2. Verify /me endpoint for Guardian
        me_resp = await client.get("/api/v1/auth/me", headers=guardian_headers)
        assert me_resp.status_code == 200
        assert me_resp.json()["data"]["email"] == "elena.guardian@kidsync.ai"

        # 3. Register Caregiver User
        caregiver_user_resp = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "maria.caregiver@kidsync.ai",
                "password": "NannyPassword456!",
                "first_name": "Maria",
                "last_name": "Santos",
                "phone": "+15550183344",
                "role": "CARE_PROVIDER",
            },
        )
        assert caregiver_user_resp.status_code == 201
        caregiver_user_data = caregiver_user_resp.json()["data"]
        caregiver_user_id = caregiver_user_data["user"]["id"]
        caregiver_token = caregiver_user_data["access_token"]
        caregiver_headers = {"Authorization": f"Bearer {caregiver_token}"}

        # 4. Create Caregiver Profile
        caregiver_profile_resp = await client.post(
            "/api/v1/caregivers/",
            headers=caregiver_headers,
            json={
                "user_id": caregiver_user_id,
                "bio": "Certified pediatric nanny with 6 years experience specializing in toddlers.",
                "years_of_experience": 6,
                "hourly_rate_cents": 2500,  # $25.00/hour
                "currency": "USD",
                "specialties": ["INFANT_CARE", "FIRST_AID", "SENSORY_SUPPORT"],
                "certifications": [{"name": "Pediatric First Aid & CPR", "issuer": "Red Cross"}],
                "emergency_phone": "+15550198888",
                "is_available": True,
            },
        )
        assert caregiver_profile_resp.status_code == 201, caregiver_profile_resp.text
        caregiver_profile = caregiver_profile_resp.json()["data"]
        caregiver_id = caregiver_profile["id"]

        # Update caregiver to PASSED background check
        update_cg_resp = await client.put(
            f"/api/v1/caregivers/{caregiver_id}",
            headers=guardian_headers,
            json={"background_check_status": "PASSED"},
        )
        assert update_cg_resp.status_code == 200
        assert update_cg_resp.json()["data"]["background_check_status"] == "PASSED"

        # 5. Assign Caregiver to Guardian Family
        assign_resp = await client.post(
            f"/api/v1/caregivers/{caregiver_id}/assign",
            headers=guardian_headers,
            json={
                "caregiver_id": caregiver_id,
                "role_type": "CARE_PROVIDER",
                "can_view_health": True,
                "can_view_schedule": True,
                "can_view_financials": False,
                "can_administer_meds": True,
            },
        )
        assert assign_resp.status_code == 201, assign_resp.text
        assert assign_resp.json()["data"]["can_view_health"] is True

        # 6. Create Childcare Booking Request
        start_dt = datetime.now(timezone.utc) + timedelta(days=1, hours=2)
        end_dt = start_dt + timedelta(hours=3)  # 3 hours = 3 * 2500 = 7500 cents ($75.00)

        booking_resp = await client.post(
            "/api/v1/bookings/",
            headers=guardian_headers,
            json={
                "caregiver_id": caregiver_id,
                "start_time": start_dt.isoformat(),
                "end_time": end_dt.isoformat(),
                "special_instructions": "Maya takes a 1.5h nap around 1:30 PM. Please give water.",
            },
        )
        assert booking_resp.status_code == 201, booking_resp.text
        booking_data = booking_resp.json()["data"]
        booking_id = booking_data["id"]
        assert booking_data["status"] == "PENDING"
        assert booking_data["total_amount_cents"] == 7500

        # 7. Attempt Overlapping Booking (Should return HTTP 409 Conflict)
        clash_start = start_dt + timedelta(hours=1)
        clash_end = start_dt + timedelta(hours=4)
        overlap_resp = await client.post(
            "/api/v1/bookings/",
            headers=guardian_headers,
            json={
                "caregiver_id": caregiver_id,
                "start_time": clash_start.isoformat(),
                "end_time": clash_end.isoformat(),
            },
        )
        assert overlap_resp.status_code == 409, overlap_resp.text
        assert overlap_resp.json()["error_code"] == "RESOURCE_CONFLICT"

        # 8. Transition Booking to CONFIRMED
        status_resp = await client.patch(
            f"/api/v1/bookings/{booking_id}/status",
            headers=caregiver_headers,
            json={"status": "CONFIRMED"},
        )
        assert status_resp.status_code == 200, status_resp.text
        assert status_resp.json()["data"]["status"] == "CONFIRMED"

        # 9. Verify Cryptographic Audit Ledger
        audit_verify_resp = await client.get("/api/v1/audit/verify", headers=guardian_headers)
        assert audit_verify_resp.status_code == 200, audit_verify_resp.text
        audit_result = audit_verify_resp.json()["data"]
        assert audit_result["is_valid"] is True, f"Audit verification failed: {audit_result}"
        assert audit_result["total_entries_checked"] > 0
        assert audit_result["root_hash"] is not None
        assert "Zero tampering detected" in audit_result["verification_message"]
