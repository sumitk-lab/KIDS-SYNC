"""Caregiver profiles and family assignment endpoints."""

import uuid
from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_client_ip, get_current_user, get_db, require_roles
from src.models.user import UserModel
from src.schemas.caregiver import (
    CaregiverAssignmentCreate,
    CaregiverAssignmentResponse,
    CaregiverCreate,
    CaregiverResponse,
    CaregiverUpdate,
)
from src.schemas.common import ApiResponse, PaginatedResponse
from src.services.caregiver_service import CaregiverService

router = APIRouter(prefix="/caregivers", tags=["Caregivers"])


@router.post(
    "/",
    response_model=ApiResponse[CaregiverResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Register a new caregiver profile",
)
async def create_caregiver(
    data: CaregiverCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> ApiResponse[CaregiverResponse]:
    """Onboard a caregiver profile linked to a registered user account."""
    client_ip = get_client_ip(request)
    service = CaregiverService(db)
    created = await service.create_caregiver_profile(
        data=data,
        actor_id=current_user.id,
        client_ip=client_ip,
    )
    return ApiResponse(
        success=True,
        message="Caregiver profile created successfully.",
        data=CaregiverResponse.model_validate(created),
    )


@router.get(
    "/",
    response_model=PaginatedResponse[CaregiverResponse],
    summary="List available caregivers (Paginated)",
)
async def list_available_caregivers(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _: UserModel = Depends(get_current_user),
) -> PaginatedResponse[CaregiverResponse]:
    """List caregivers that are verified and currently accepting bookings."""
    skip = (page - 1) * page_size
    service = CaregiverService(db)
    items, total = await service.list_available(skip=skip, limit=page_size)

    dtos = [CaregiverResponse.model_validate(c) for c in items]
    return PaginatedResponse(
        items=dtos,
        total_count=total,
        page=page,
        page_size=page_size,
        has_next=(skip + len(dtos)) < total,
    )


@router.get(
    "/{caregiver_id}",
    response_model=ApiResponse[CaregiverResponse],
    summary="Get caregiver profile by ID",
)
async def get_caregiver(
    caregiver_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: UserModel = Depends(get_current_user),
) -> ApiResponse[CaregiverResponse]:
    """Retrieve full caregiver profile including vetting status and ratings."""
    service = CaregiverService(db)
    caregiver = await service.get_by_id(caregiver_id)
    return ApiResponse(
        success=True,
        message="Caregiver profile retrieved successfully.",
        data=CaregiverResponse.model_validate(caregiver),
    )


@router.put(
    "/{caregiver_id}",
    response_model=ApiResponse[CaregiverResponse],
    summary="Update caregiver profile",
)
async def update_caregiver(
    caregiver_id: uuid.UUID,
    data: CaregiverUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> ApiResponse[CaregiverResponse]:
    """Update caregiver rates, specialties, availability, or vetting status."""
    client_ip = get_client_ip(request)
    service = CaregiverService(db)
    updated = await service.update_profile(
        caregiver_id=caregiver_id,
        data=data,
        actor_id=current_user.id,
        client_ip=client_ip,
    )
    return ApiResponse(
        success=True,
        message="Caregiver profile updated successfully.",
        data=CaregiverResponse.model_validate(updated),
    )


@router.post(
    "/{caregiver_id}/assign",
    response_model=ApiResponse[CaregiverAssignmentResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Assign caregiver to family circle with permissions",
    dependencies=[Depends(require_roles("PRIMARY_GUARDIAN", "ADMIN"))],
)
async def assign_caregiver_to_family(
    caregiver_id: uuid.UUID,
    data: CaregiverAssignmentCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> ApiResponse[CaregiverAssignmentResponse]:
    """Delegate family routine and health access permissions to a caregiver."""
    client_ip = get_client_ip(request)
    service = CaregiverService(db)
    # Ensure caregiver_id from path matches schema
    data.caregiver_id = caregiver_id
    assignment = await service.assign_caregiver(
        assigned_by_user_id=current_user.id,
        data=data,
        client_ip=client_ip,
    )
    return ApiResponse(
        success=True,
        message="Caregiver assigned to family circle successfully.",
        data=CaregiverAssignmentResponse.model_validate(assignment),
    )
