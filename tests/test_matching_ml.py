"""Tests for Autonomous Matching, PyTorch Two-Tower Ranking, and Dynamic Trust Engine."""

import os
from datetime import datetime, timedelta, timezone
import pytest
import pytest_asyncio
import torch
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.api.deps import get_db
from src.core.database import Base
from src.main import app
from src.ml.models import (
    TwoTowerRankingModel,
    vectorize_caregiver,
    vectorize_family_request,
)
from src.ml.trust_engine import DynamicTrustEngine



# ------------------------------------------------------------------------------
# 1. DYNAMIC TRUST ENGINE UNIT TESTS
# ------------------------------------------------------------------------------
def test_dynamic_trust_engine_platinum():
    """Verify high-trust caregiver receives PLATINUM tier and score >= 88.0."""
    now = datetime.now(timezone.utc)
    recent_check = now - timedelta(days=45)

    breakdown = DynamicTrustEngine.compute_trust_score(
        background_check_status="PASSED",
        background_checked_at=recent_check,
        years_of_experience=8,
        certifications=[
            {"name": "Pediatric First Aid & CPR", "issuer": "Red Cross"},
            {"name": "Special Needs Care Specialist", "issuer": "Early Intervention"},
        ],
        specialties=["INFANT_CARE", "FIRST_AID", "SENSORY_SUPPORT"],
        rating_average=4.95,
        total_reviews=28,
        completed_bookings=42,
        cancelled_by_caregiver_bookings=1,
        safety_incident_count=0,
        is_identity_verified=True,
    )

    assert breakdown.overall_trust_score >= 88.0
    assert breakdown.trust_tier == "PLATINUM"
    assert breakdown.identity_score == 100.0
    assert breakdown.safety_score == 100.0


def test_dynamic_trust_engine_probationary():
    """Verify new or unverified caregiver receives PROBATIONARY tier."""
    breakdown = DynamicTrustEngine.compute_trust_score(
        background_check_status="PENDING",
        background_checked_at=None,
        years_of_experience=0,
        certifications=[],
        specialties=[],
        rating_average=5.0,
        total_reviews=0,
        completed_bookings=0,
        cancelled_by_caregiver_bookings=0,
        safety_incident_count=0,
        is_identity_verified=False,
    )

    assert breakdown.overall_trust_score < 60.0
    assert breakdown.trust_tier == "PROBATIONARY"
    assert breakdown.identity_score <= 35.0


def test_dynamic_trust_safety_penalty():
    """Verify safety incidents significantly penalize trust score."""
    breakdown_clean = DynamicTrustEngine.compute_trust_score(
        background_check_status="PASSED",
        background_checked_at=datetime.now(timezone.utc),
        years_of_experience=5,
        certifications=[{"name": "CPR"}],
        specialties=["INFANT_CARE"],
        rating_average=4.8,
        total_reviews=10,
        safety_incident_count=0,
    )

    breakdown_incident = DynamicTrustEngine.compute_trust_score(
        background_check_status="PASSED",
        background_checked_at=datetime.now(timezone.utc),
        years_of_experience=5,
        certifications=[{"name": "CPR"}],
        specialties=["INFANT_CARE"],
        rating_average=4.8,
        total_reviews=10,
        safety_incident_count=1,
    )

    assert breakdown_incident.safety_score == 60.0  # 100 - 40
    assert breakdown_incident.overall_trust_score < breakdown_clean.overall_trust_score
    assert any("safety incident" in note.lower() for note in breakdown_incident.verification_notes)


# ------------------------------------------------------------------------------
# 2. PYTORCH TWO-TOWER RANKING MODEL UNIT TESTS
# ------------------------------------------------------------------------------
def test_pytorch_two_tower_model_forward():
    """Test PyTorch TwoTowerRankingModel tensor dimensions and output bounds."""
    model = TwoTowerRankingModel()
    model.eval()

    fam_vec = vectorize_family_request(
        child_age_years=2.5,
        has_special_needs=True,
        required_specialties=["INFANT_CARE", "FIRST_AID"],
        max_hourly_rate_cents=3500,
        session_duration_hours=4.0,
        min_trust_score=70.0,
    )
    assert fam_vec.shape == (16,)

    cg_vec = vectorize_caregiver(
        specialties=["INFANT_CARE", "FIRST_AID", "SENSORY_SUPPORT"],
        years_of_experience=6,
        hourly_rate_cents=3000,
        rating_average=4.9,
        total_reviews_count=15,
        trust_score=85.0,
        background_check_status="PASSED",
    )
    assert cg_vec.shape == (16,)

    ctx_vec = torch.tensor([0.85, 1.0, 1.0], dtype=torch.float32)

    with torch.no_grad():
        match_scores, cosine_sims = model(
            fam_vec.unsqueeze(0),
            cg_vec.unsqueeze(0),
            ctx_vec.unsqueeze(0),
        )

    assert match_scores.shape == (1, 1)
    assert cosine_sims.shape == (1, 1)
    assert 0.0 <= match_scores.item() <= 1.0
    assert -1.0 <= cosine_sims.item() <= 1.0


# ------------------------------------------------------------------------------
# 3. END-TO-END AUTONOMOUS MATCHING & DYNAMIC TRUST API TESTS
# ------------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_autonomous_matching_and_trust_api():
    """
    E2E integration test:
    1. Register Guardian and 2 Caregivers (one high-trust, one unvetted).
    2. Query individual caregiver Dynamic Trust score endpoint.
    3. Run autonomous neural matching and verify ranking order.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Register Primary Guardian
        g_resp = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "sarah.parent@kidsync.ai",
                "password": "Password123!",
                "first_name": "Sarah",
                "last_name": "Connor",
                "role": "PRIMARY_GUARDIAN",
            },
        )
        assert g_resp.status_code == 201
        g_token = g_resp.json()["data"]["access_token"]
        g_headers = {"Authorization": f"Bearer {g_token}"}

        # 2. Register Caregiver A (High-trust, certified pediatric nanny)
        cg_a_user = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "anna.nanny@kidsync.ai",
                "password": "Password123!",
                "first_name": "Anna",
                "last_name": "Kowalski",
                "role": "CARE_PROVIDER",
            },
        )
        assert cg_a_user.status_code == 201
        cg_a_uid = cg_a_user.json()["data"]["user"]["id"]
        cg_a_token = cg_a_user.json()["data"]["access_token"]

        cg_a_prof = await client.post(
            "/api/v1/caregivers/",
            headers={"Authorization": f"Bearer {cg_a_token}"},
            json={
                "user_id": cg_a_uid,
                "bio": "Experienced infant specialist with pediatric CPR.",
                "years_of_experience": 8,
                "hourly_rate_cents": 3000,
                "currency": "USD",
                "specialties": ["INFANT_CARE", "FIRST_AID"],
                "certifications": [{"name": "Pediatric First Aid & CPR"}],
                "is_available": True,
            },
        )
        assert cg_a_prof.status_code == 201
        cg_a_id = cg_a_prof.json()["data"]["id"]

        # Vetting pass for Caregiver A
        await client.put(
            f"/api/v1/caregivers/{cg_a_id}",
            headers=g_headers,
            json={"background_check_status": "PASSED"},
        )

        # 3. Register Caregiver B (New, unvetted, higher rate)
        cg_b_user = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "brian.sitter@kidsync.ai",
                "password": "Password123!",
                "first_name": "Brian",
                "last_name": "Miller",
                "role": "CARE_PROVIDER",
            },
        )
        assert cg_b_user.status_code == 201
        cg_b_uid = cg_b_user.json()["data"]["user"]["id"]
        cg_b_token = cg_b_user.json()["data"]["access_token"]

        cg_b_prof = await client.post(
            "/api/v1/caregivers/",
            headers={"Authorization": f"Bearer {cg_b_token}"},
            json={
                "user_id": cg_b_uid,
                "bio": "Occasional weekend sitter.",
                "years_of_experience": 1,
                "hourly_rate_cents": 5500,
                "currency": "USD",
                "specialties": ["HOMEWORK_TUTOR"],
                "is_available": True,
            },
        )
        assert cg_b_prof.status_code == 201
        cg_b_id = cg_b_prof.json()["data"]["id"]

        # 4. Check Individual Caregiver Dynamic Trust Scores
        trust_a_resp = await client.get(
            f"/api/v1/matching/trust-score/{cg_a_id}",
            headers=g_headers,
        )
        assert trust_a_resp.status_code == 200, trust_a_resp.text
        trust_a_data = trust_a_resp.json()["data"]["breakdown"]
        assert trust_a_data["overall_trust_score"] >= 75.0
        assert trust_a_data["trust_tier"] in ["PLATINUM", "GOLD"]

        trust_b_resp = await client.get(
            f"/api/v1/matching/trust-score/{cg_b_id}",
            headers=g_headers,
        )
        assert trust_b_resp.status_code == 200
        trust_b_data = trust_b_resp.json()["data"]["breakdown"]
        assert trust_b_data["trust_tier"] == "PROBATIONARY"
        assert trust_b_data["overall_trust_score"] < trust_a_data["overall_trust_score"]

        # 5. Execute Autonomous Matching & Neural Ranking for Infant Care
        match_resp = await client.post(
            "/api/v1/matching/rank",
            headers=g_headers,
            json={
                "child_age_years": 0.8,  # Infant (<1 yr)
                "has_special_needs": False,
                "required_specialties": ["INFANT_CARE", "FIRST_AID"],
                "max_hourly_rate_cents": 4000,
                "session_duration_hours": 4.0,
                "min_trust_score": 40.0,
                "top_k": 5,
            },
        )
        assert match_resp.status_code == 200, match_resp.text
        match_data = match_resp.json()["data"]
        assert match_data["total_candidates_evaluated"] >= 2
        assert len(match_data["matched_candidates"]) >= 1

        # Caregiver A should be top-ranked due to higher trust, CPR cert, and infant specialty
        top_candidate = match_data["matched_candidates"][0]
        assert top_candidate["caregiver_id"] == cg_a_id
        assert top_candidate["first_name"] == "Anna"
        assert top_candidate["match_score"] > 60.0
        assert "Trust" in top_candidate["recommendation_reason"]
