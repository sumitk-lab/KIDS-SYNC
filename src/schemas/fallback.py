"""Automated backup caregiver fallback workflow schemas."""

import uuid
from typing import List, Optional
from pydantic import Field

from src.schemas.common import KidSyncBaseSchema


class BackupTriggerRequest(KidSyncBaseSchema):
    """Schema to trigger backup caregiver fallback protocol."""

    booking_id: uuid.UUID
    reason: str = Field(min_length=3, max_length=500, description="Reason for fallback (e.g. unresponsiveness, emergency).")
    auto_assign: bool = Field(default=True, description="Automatically reassign booking to top ranked backup.")


class BackupCandidateOffer(KidSyncBaseSchema):
    """Candidate backup caregiver ranked by PyTorch Two-Tower model."""

    caregiver_id: uuid.UUID
    name: str
    trust_score: float
    match_score: float
    hourly_rate_cents: int
    specialties: List[str]
    offer_status: str = "OFFERED"  # OFFERED, ACCEPTED, DECLINED


class BackupFallbackWorkflowResponse(KidSyncBaseSchema):
    """Status and resolution of the automated backup fallback workflow."""

    booking_id: uuid.UUID
    status: str  # FALLBACK_TRIGGERED, BACKUP_ASSIGNED, MANUAL_REVIEW_REQUIRED
    original_caregiver_id: uuid.UUID
    backup_caregiver_id: Optional[uuid.UUID] = None
    assigned_caregiver_name: Optional[str] = None
    fallback_reason: str
    ranked_backup_candidates: List[BackupCandidateOffer]
    message: str
