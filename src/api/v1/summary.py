"""NLP End-of-Day (EOD) summary API endpoints."""

import uuid
from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_client_ip, get_current_user, get_db
from src.models.user import UserModel
from src.schemas.common import ApiResponse
from src.schemas.summary import (
    EODMetrics,
    EODSummaryGenerateRequest,
    EODSummaryResponse,
)
from src.services.nlp_summary_service import NLPSummaryService

router = APIRouter(prefix="/summary", tags=["NLP End-of-Day Transition Summaries"])


@router.post(
    "/generate",
    response_model=ApiResponse[EODSummaryResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Generate NLP-driven End-of-Day transition summary from telemetry",
)
async def generate_eod_summary(
    request_data: EODSummaryGenerateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> ApiResponse[EODSummaryResponse]:
    """
    NLP End-of-Day Digest Engine:
    Synthesizes session telemetry (meals, sleep duration, medications administered, mood trends, incidents)
    into a structured transition briefing and actionable highlights for parents.
    """
    client_ip = get_client_ip(request)
    service = NLPSummaryService(db)
    summary_model = await service.generate_eod_summary(
        booking_id=request_data.booking_id,
        child_name=request_data.child_name or "Child",
        actor_id=current_user.id,
        client_ip=client_ip,
    )

    metrics_obj = EODMetrics(**(summary_model.metrics or {}))
    response_dto = EODSummaryResponse(
        id=summary_model.id,
        booking_id=summary_model.booking_id,
        summary_text=summary_model.summary_text,
        highlights=summary_model.highlights,
        metrics=metrics_obj,
        action_items=summary_model.action_items,
        generated_at=summary_model.generated_at,
        acknowledged_at=summary_model.acknowledged_at,
    )

    return ApiResponse(
        success=True,
        message="NLP End-of-Day transition summary synthesized successfully.",
        data=response_dto,
    )


@router.get(
    "/{booking_id}",
    response_model=ApiResponse[EODSummaryResponse],
    summary="Get existing End-of-Day summary for a childcare session",
)
async def get_eod_summary(
    booking_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: UserModel = Depends(get_current_user),
) -> ApiResponse[EODSummaryResponse]:
    """Retrieve existing synthesized EOD summary for a session."""
    service = NLPSummaryService(db)
    summary_model = await service.get_summary_by_booking(booking_id)

    metrics_obj = EODMetrics(**(summary_model.metrics or {}))
    response_dto = EODSummaryResponse(
        id=summary_model.id,
        booking_id=summary_model.booking_id,
        summary_text=summary_model.summary_text,
        highlights=summary_model.highlights,
        metrics=metrics_obj,
        action_items=summary_model.action_items,
        generated_at=summary_model.generated_at,
        acknowledged_at=summary_model.acknowledged_at,
    )

    return ApiResponse(
        success=True,
        message="EOD summary retrieved.",
        data=response_dto,
    )
