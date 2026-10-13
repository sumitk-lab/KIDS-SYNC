"""Dynamic Trust Score calculation engine for caregiver verification and matching."""

import math
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


from src.schemas.matching import TrustBreakdown


class DynamicTrustEngine:
    """
    Engine calculating multi-pillar dynamic trust scores for caregivers.
    Weights:
      - Identity & Background Check: 30%
      - Competency & Certifications: 25%
      - Reliability & Performance:   25%
      - Safety & Incident Integrity: 20%
    """

    W_IDENTITY: float = 0.30
    W_COMPETENCY: float = 0.25
    W_RELIABILITY: float = 0.25
    W_SAFETY: float = 0.20

    # Bayesian rating prior parameters
    BAYESIAN_C: float = 5.0  # Equivalent prior votes
    BAYESIAN_PRIOR_MEAN: float = 4.5  # Prior rating

    @classmethod
    def compute_trust_score(
        cls,
        background_check_status: str,
        background_checked_at: Optional[datetime],
        years_of_experience: int,
        certifications: List[Dict[str, Any]],
        specialties: List[str],
        rating_average: float,
        total_reviews: int,
        completed_bookings: int = 0,
        cancelled_by_caregiver_bookings: int = 0,
        safety_incident_count: int = 0,
        is_identity_verified: bool = True,
    ) -> TrustBreakdown:
        """Calculate the comprehensive dynamic trust score for a caregiver."""
        notes: List[str] = []

        # ----------------------------------------------------------------------
        # 1. Identity & Background Verification (0 - 100)
        # ----------------------------------------------------------------------
        id_score = 0.0
        status_upper = (background_check_status or "PENDING").upper()

        if status_upper == "PASSED":
            id_score = 85.0
            # Recency bonus/penalty
            if background_checked_at:
                now = datetime.now(timezone.utc)
                if background_checked_at.tzinfo is None:
                    bg_dt = background_checked_at.replace(tzinfo=timezone.utc)
                else:
                    bg_dt = background_checked_at.astimezone(timezone.utc)
                days_since = (now - bg_dt).days
                if days_since <= 180:
                    id_score += 15.0  # Verified within 6 months
                    notes.append("Background check verified within 6 months (+15pts).")
                elif days_since <= 365:
                    id_score += 10.0
                else:
                    id_score -= 10.0
                    notes.append("Background check older than 1 year (-10pts decay).")
            else:
                id_score += 10.0
        elif status_upper == "PENDING":
            id_score = 30.0
            notes.append("Background check is currently pending review.")
        else:
            id_score = 0.0
            notes.append("Background check not passed or expired.")

        if is_identity_verified:
            id_score = min(100.0, id_score + 5.0)

        id_score = max(0.0, min(100.0, id_score))

        # ----------------------------------------------------------------------
        # 2. Competency & Certifications (0 - 100)
        # ----------------------------------------------------------------------
        comp_score = 20.0  # Baseline
        # Experience curve
        exp_pts = min(40.0, years_of_experience * 6.5)
        comp_score += exp_pts

        # Certifications value
        cert_names = [str(c.get("name", "")).upper() for c in (certifications or [])]
        cert_pts = 0.0
        for name in cert_names:
            if any(k in name for k in ["CPR", "FIRST AID", "BLS"]):
                cert_pts += 20.0
            elif any(k in name for k in ["SPECIAL NEEDS", "AUTISM", "ADHD"]):
                cert_pts += 15.0
            elif any(k in name for k in ["PEDIATRIC", "INFANT", "ECE", "MONTESSORI"]):
                cert_pts += 15.0
            else:
                cert_pts += 10.0
        comp_score += min(40.0, cert_pts)

        if len(specialties or []) >= 2:
            comp_score = min(100.0, comp_score + 5.0)

        comp_score = max(0.0, min(100.0, comp_score))

        # ----------------------------------------------------------------------
        # 3. Reliability & Performance (0 - 100)
        # ----------------------------------------------------------------------
        # Bayesian smoothed rating
        total_votes = total_reviews
        bayes_rating = (
            (cls.BAYESIAN_C * cls.BAYESIAN_PRIOR_MEAN + (rating_average * total_votes))
            / (cls.BAYESIAN_C + total_votes)
        )
        rating_score = (bayes_rating / 5.0) * 100.0

        # Booking completion rate
        total_scheduled = completed_bookings + cancelled_by_caregiver_bookings
        if total_scheduled > 0:
            completion_rate = (completed_bookings / total_scheduled) * 100.0
        else:
            completion_rate = 85.0  # Neutral prior for new caregivers

        rel_score = 0.60 * rating_score + 0.40 * completion_rate
        rel_score = max(0.0, min(100.0, rel_score))

        # ----------------------------------------------------------------------
        # 4. Safety & Audit Integrity (0 - 100)
        # ----------------------------------------------------------------------
        safety_score = 100.0
        if safety_incident_count > 0:
            penalty = min(80.0, safety_incident_count * 40.0)
            safety_score -= penalty
            notes.append(f"Recorded {safety_incident_count} safety incidents in audit ledger (-{penalty}pts).")

        safety_score = max(0.0, min(100.0, safety_score))

        # ----------------------------------------------------------------------
        # Composite Trust Score
        # ----------------------------------------------------------------------
        overall = (
            cls.W_IDENTITY * id_score
            + cls.W_COMPETENCY * comp_score
            + cls.W_RELIABILITY * rel_score
            + cls.W_SAFETY * safety_score
        )
        overall = round(max(0.0, min(100.0, overall)), 2)

        # Tier assignment
        if overall >= 88.0 and status_upper == "PASSED":
            tier = "PLATINUM"
        elif overall >= 75.0 and status_upper == "PASSED":
            tier = "GOLD"
        elif overall >= 60.0:
            tier = "SILVER"
        else:
            tier = "PROBATIONARY"

        return TrustBreakdown(
            identity_score=round(id_score, 2),
            competency_score=round(comp_score, 2),
            reliability_score=round(rel_score, 2),
            safety_score=round(safety_score, 2),
            overall_trust_score=overall,
            trust_tier=tier,
            verification_notes=notes,
        )
