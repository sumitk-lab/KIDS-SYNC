"""User management endpoints."""

import uuid
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_client_ip, get_current_user, get_db, require_roles
from src.models.user import UserModel
from src.schemas.common import ApiResponse, PaginatedResponse
from src.schemas.user import UserResponse, UserUpdate
from src.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["Users"])


@router.get(
    "/",
    response_model=PaginatedResponse[UserResponse],
    summary="List users (Paginated)",
    dependencies=[Depends(require_roles("PRIMARY_GUARDIAN", "ADMIN"))],
)
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[UserResponse]:
    """List users with pagination."""
    skip = (page - 1) * page_size
    service = UserService(db)
    items, total = await service.list_users(skip=skip, limit=page_size)

    dtos = [UserResponse.model_validate(u) for u in items]
    return PaginatedResponse(
        items=dtos,
        total_count=total,
        page=page,
        page_size=page_size,
        has_next=(skip + len(dtos)) < total,
    )


@router.get(
    "/{user_id}",
    response_model=ApiResponse[UserResponse],
    summary="Get user details by ID",
)
async def get_user_by_id(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: UserModel = Depends(get_current_user),
) -> ApiResponse[UserResponse]:
    """Retrieve user profile by unique identifier."""
    service = UserService(db)
    user = await service.get_by_id(user_id)
    return ApiResponse(
        success=True,
        message="User retrieved successfully.",
        data=UserResponse.model_validate(user),
    )


@router.put(
    "/{user_id}",
    response_model=ApiResponse[UserResponse],
    summary="Update user profile",
)
async def update_user(
    user_id: uuid.UUID,
    data: UserUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> ApiResponse[UserResponse]:
    """Update profile attributes and record change in audit ledger."""
    client_ip = get_client_ip(request)
    service = UserService(db)
    updated = await service.update_user(
        user_id=user_id,
        data=data,
        actor_id=current_user.id,
        client_ip=client_ip,
    )
    return ApiResponse(
        success=True,
        message="User profile updated successfully.",
        data=UserResponse.model_validate(updated),
    )
