"""Booking endpoints for childcare sessions and scheduling."""

import uuid
from typing import List
from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_client_ip, get_current_user, get_db
from src.models.user import UserModel
from src.schemas.booking import (
    BookingCreate,
    BookingResponse,
    BookingStatusUpdate,
)
from src.schemas.common import ApiResponse
from src.services.booking_service import BookingService

router = APIRouter(prefix="/bookings", tags=["Bookings"])


@router.post(
    "/",
    response_model=ApiResponse[BookingResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create a new childcare booking request",
)
async def create_booking(
    data: BookingCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> ApiResponse[BookingResponse]:
    """Request a childcare booking with verified caregiver availability and automated cost calculation."""
    client_ip = get_client_ip(request)
    service = BookingService(db)
    booking = await service.create_booking(
        client_user_id=current_user.id,
        data=data,
        client_ip=client_ip,
    )
    return ApiResponse(
        success=True,
        message="Childcare booking request submitted successfully.",
        data=BookingResponse.model_validate(booking),
    )


@router.get(
    "/",
    response_model=ApiResponse[List[BookingResponse]],
    summary="List bookings for the current user",
)
async def list_my_bookings(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> ApiResponse[List[BookingResponse]]:
    """Retrieve bookings where the authenticated user is the requesting client."""
    skip = (page - 1) * page_size
    service = BookingService(db)
    bookings = await service.list_for_client(
        client_user_id=current_user.id,
        skip=skip,
        limit=page_size,
    )
    dtos = [BookingResponse.model_validate(b) for b in bookings]
    return ApiResponse(
        success=True,
        message="Bookings retrieved successfully.",
        data=dtos,
    )


@router.get(
    "/{booking_id}",
    response_model=ApiResponse[BookingResponse],
    summary="Get booking details by ID",
)
async def get_booking(
    booking_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: UserModel = Depends(get_current_user),
) -> ApiResponse[BookingResponse]:
    """Retrieve booking session details, timing, total cost, and status."""
    service = BookingService(db)
    booking = await service.get_by_id(booking_id)
    return ApiResponse(
        success=True,
        message="Booking details retrieved.",
        data=BookingResponse.model_validate(booking),
    )


@router.patch(
    "/{booking_id}/status",
    response_model=ApiResponse[BookingResponse],
    summary="Update booking status (Confirm, Cancel, Complete, Reject)",
)
async def update_booking_status(
    booking_id: uuid.UUID,
    data: BookingStatusUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> ApiResponse[BookingResponse]:
    """Execute status transition on a booking and record the transition in the cryptographic audit ledger."""
    client_ip = get_client_ip(request)
    service = BookingService(db)
    updated = await service.update_status(
        booking_id=booking_id,
        data=data,
        actor_id=current_user.id,
        client_ip=client_ip,
    )
    return ApiResponse(
        success=True,
        message=f"Booking status transitioned to {data.status.value}.",
        data=BookingResponse.model_validate(updated),
    )
