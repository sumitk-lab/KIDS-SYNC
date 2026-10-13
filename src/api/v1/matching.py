"""Autonomous matching and Dynamic Trust API endpoints."""

import uuid
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_current_user, get_db
from src.ml.ranking_service import AutonomousMatchingService
from src.models.user import UserModel
from src.schemas.common import ApiResponse
from src.schemas.matching import (
    CaregiverMatchRequest,
    CaregiverMatchResponse,
    TrustScoreResponse,
)

router = APIRouter(prefix="/matching", tags=["Autonomous Matching & Dynamic Trust"])


@router.post(
    "/rank",
    response_model=ApiResponse[CaregiverMatchResponse],
    status_code=status.HTTP_200_OK,
    summary="Rank caregivers using PyTorch Two-Tower embeddings & Dynamic Trust",
)
async def rank_caregivers(
    request: CaregiverMatchRequest,
    db: AsyncSession = Depends(get_db),
    _: UserModel = Depends(get_current_user),
) -> ApiResponse[CaregiverMatchResponse]:
    """
    Autonomous Caregiver Matching Pipeline:
    1. Evaluates all active vetted caregivers against family requirements.
    2. Computes multi-pillar Dynamic Trust Scores (Identity, Competency, Reliability, Safety).
    3. Runs PyTorch Two-Tower embedding model to compute semantic compatibility vectors.
    4. Returns ranked candidates with explainable recommendation rationale.
    """
    service = AutonomousMatchingService(db)
    result = await service.match_and_rank_caregivers(request)
    return ApiResponse(
        success=True,
        message=f"Matched and ranked {len(result.matched_candidates)} top caregiver candidates.",
        data=result,
    )


@router.get(
    "/trust-score/{caregiver_id}",
    response_model=ApiResponse[TrustScoreResponse],
    summary="Retrieve real-time Dynamic Trust Score breakdown for a caregiver",
)
async def get_caregiver_trust_score(
    caregiver_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: UserModel = Depends(get_current_user),
) -> ApiResponse[TrustScoreResponse]:
    """
    Computes real-time Dynamic Trust Score breakdown across Identity,
    Competency, Reliability (Bayesian reviews & completion rate), and Safety audit logs.
    """
    service = AutonomousMatchingService(db)
    result = await service.get_caregiver_trust_breakdown(caregiver_id)
    return ApiResponse(
        success=True,
        message="Dynamic Trust Score calculated successfully.",
        data=result,
    )
