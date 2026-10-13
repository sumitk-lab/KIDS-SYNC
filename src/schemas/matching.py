"""Autonomous matching and Dynamic Trust Score schemas with Pydantic v2 validation."""

import uuid
from typing import List, Optional
from pydantic import Field

from src.schemas.common import KidSyncBaseSchema


class TrustBreakdown(KidSyncBaseSchema):
    """Component scores of the Dynamic Trust calculation (0.0 to 100.0)."""

    identity_score: float = Field(ge=0.0, le=100.0)
    competency_score: float = Field(ge=0.0, le=100.0)
    reliability_score: float = Field(ge=0.0, le=100.0)
    safety_score: float = Field(ge=0.0, le=100.0)
    overall_trust_score: float = Field(ge=0.0, le=100.0)
    trust_tier: str  # "PLATINUM", "GOLD", "SILVER", "PROBATIONARY"
    verification_notes: List[str] = Field(default_factory=list)


class CaregiverMatchRequest(KidSyncBaseSchema):
    """Schema for family caregiver matching and neural ranking requests."""

    child_age_years: float = Field(default=3.0, ge=0.0, le=18.0, description="Age of the child in years.")
    has_special_needs: bool = Field(default=False, description="Whether child requires neurodivergent/sensory care.")
    required_specialties: List[str] = Field(default_factory=list, description="Requested skills (e.g., CPR, INFANT_CARE).")
    max_hourly_rate_cents: int = Field(default=5000, ge=1000, le=20000, description="Maximum budget in cents ($50 max).")
    session_duration_hours: float = Field(default=3.0, ge=0.5, le=24.0, description="Estimated duration in hours.")
    min_trust_score: float = Field(default=50.0, ge=0.0, le=100.0, description="Minimum acceptable trust threshold.")
    top_k: int = Field(default=10, ge=1, le=50, description="Number of top candidates to return.")


class CaregiverMatchCandidate(KidSyncBaseSchema):
    """Detailed score card and profile of a matched caregiver."""

    caregiver_id: uuid.UUID
    user_id: uuid.UUID
    first_name: str
    last_name: str
    hourly_rate_cents: int
    years_of_experience: int
    specialties: List[str]
    rating_average: float
    total_reviews_count: int
    trust_breakdown: TrustBreakdown
    cosine_similarity: float
    match_score: float = Field(description="Normalized neural match confidence (0.0 to 100.0).")
    recommendation_reason: str


class CaregiverMatchResponse(KidSyncBaseSchema):
    """Result of autonomous neural matching pipeline."""

    total_candidates_evaluated: int
    matched_candidates: List[CaregiverMatchCandidate]
    top_match_id: Optional[uuid.UUID] = None
    query_summary: str


class TrustScoreResponse(KidSyncBaseSchema):
    """Schema for individual caregiver dynamic trust breakdown endpoint."""

    caregiver_id: uuid.UUID
    breakdown: TrustBreakdown
