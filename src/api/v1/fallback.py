"""Automated backup caregiver fallback API endpoints."""

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_client_ip, get_current_user, get_db
from src.models.user import UserModel
from src.schemas.common import ApiResponse
from src.schemas.fallback import (
    BackupFallbackWorkflowResponse,
    BackupTriggerRequest,
)
from src.services.fallback_service import BackupFallbackService

router = APIRouter(prefix="/fallback", tags=["Automated Backup Fallback Workflows"])


@router.post(
    "/trigger",
    response_model=ApiResponse[BackupFallbackWorkflowResponse],
    status_code=status.HTTP_200_OK,
    summary="Trigger automated backup caregiver fallback workflow",
)
async def trigger_backup_fallback(
    request_data: BackupTriggerRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> ApiResponse[BackupFallbackWorkflowResponse]:
    """
    Automated Backup Caregiver Fallback Workflow:
    1. Triggers emergency replacement when a primary caregiver cancels or is unresponsive.
    2. Runs PyTorch Two-Tower matching model and Dynamic Trust filter to identify top-k backups.
    3. If auto_assign is enabled, immediately reassigns the booking to the highest-trust candidate.
    4. Records the reassignment in the cryptographic audit ledger and notifies subscribers via WebSockets.
    """
    client_ip = get_client_ip(request)
    service = BackupFallbackService(db)
    result = await service.execute_fallback_workflow(
        request=request_data,
        actor_id=current_user.id,
        client_ip=client_ip,
    )
    return ApiResponse(
        success=True,
        message=result.message,
        data=result,
    )
