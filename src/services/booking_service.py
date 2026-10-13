"""Childcare booking and session management service."""

import math
import uuid
from typing import List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import ConflictError, ResourceNotFoundError, ValidationError
from src.models.booking import BookingModel
from src.repositories.booking_repo import BookingRepository
from src.repositories.caregiver_repo import CaregiverRepository
from src.schemas.booking import BookingCreate, BookingStatusUpdate, BookingUpdate
from src.services.audit_service import AuditService


class BookingService:
    """Service handling booking workflows, overlap checking, cost calculations, and audit logging."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = BookingRepository(session)
        self.caregiver_repo = CaregiverRepository(session)
        self.audit_service = AuditService(session)

    async def create_booking(
        self,
        client_user_id: uuid.UUID,
        data: BookingCreate,
        client_ip: Optional[str] = None,
    ) -> BookingModel:
        """Create a new childcare booking request with schedule overlap and rate verification."""
        # 1. Fetch caregiver
        caregiver = await self.caregiver_repo.get_by_id(data.caregiver_id)
        if not caregiver:
            raise ResourceNotFoundError("Caregiver", data.caregiver_id)

        if not caregiver.is_available:
            raise ValidationError("Caregiver is not currently accepting bookings.")

        # 2. Check for overlapping bookings
        has_overlap = await self.repo.check_overlap(
            caregiver_id=data.caregiver_id,
            start_time=data.start_time,
            end_time=data.end_time,
        )
        if has_overlap:
            raise ConflictError(
                "Caregiver already has an existing booking or reservation overlapping with the requested time."
            )

        # 3. Calculate total amount in cents
        duration_seconds = (data.end_time - data.start_time).total_seconds()
        duration_hours = duration_seconds / 3600.0
        # Round up to nearest full minute for fair pricing
        billable_hours = math.ceil(duration_hours * 60) / 60
        total_amount_cents = int(round(billable_hours * caregiver.hourly_rate_cents))

        booking = BookingModel(
            client_user_id=client_user_id,
            caregiver_id=data.caregiver_id,
            start_time=data.start_time,
            end_time=data.end_time,
            status="PENDING",
            total_amount_cents=total_amount_cents,
            currency=caregiver.currency,
            special_instructions=data.special_instructions,
            emergency_contact_override=data.emergency_contact_override,
        )
        created = await self.repo.create(booking)

        # 4. Record audit event
        await self.audit_service.log_event(
            actor_id=client_user_id,
            target_entity="bookings",
            entity_id=created.id,
            event_type="BOOKING_REQUESTED",
            payload_snapshot={
                "caregiver_id": str(created.caregiver_id),
                "start_time": created.start_time.isoformat(),
                "end_time": created.end_time.isoformat(),
                "total_amount_cents": created.total_amount_cents,
                "currency": created.currency,
            },
            client_ip=client_ip,
        )
        return created

    async def get_by_id(self, booking_id: uuid.UUID) -> BookingModel:
        """Fetch booking by ID or raise ResourceNotFoundError."""
        booking = await self.repo.get_with_details(booking_id)
        if not booking:
            raise ResourceNotFoundError("Booking", booking_id)
        return booking

    async def update_status(
        self,
        booking_id: uuid.UUID,
        data: BookingStatusUpdate,
        actor_id: uuid.UUID,
        client_ip: Optional[str] = None,
    ) -> BookingModel:
        """Update booking status (Confirm, Cancel, Complete) and append to audit chain."""
        booking = await self.get_by_id(booking_id)

        prev_status = booking.status
        new_status = data.status.value

        # State transition validation
        if prev_status in ["COMPLETED", "CANCELLED", "REJECTED"]:
            raise ConflictError(f"Cannot transition booking already in terminal state '{prev_status}'.")

        booking.status = new_status
        if data.cancellation_reason:
            booking.cancellation_reason = data.cancellation_reason

        await self.session.flush()

        # Audit event
        await self.audit_service.log_event(
            actor_id=actor_id,
            target_entity="bookings",
            entity_id=booking.id,
            event_type=f"BOOKING_STATUS_{new_status}",
            payload_snapshot={
                "previous_status": prev_status,
                "new_status": new_status,
                "cancellation_reason": data.cancellation_reason,
            },
            client_ip=client_ip,
        )
        return booking

    async def list_for_client(
        self,
        client_user_id: uuid.UUID,
        skip: int = 0,
        limit: int = 50,
    ) -> List[BookingModel]:
        """List bookings for a client."""
        return await self.repo.list_for_client(client_user_id=client_user_id, skip=skip, limit=limit)

    async def list_for_caregiver(
        self,
        caregiver_id: uuid.UUID,
        skip: int = 0,
        limit: int = 50,
    ) -> List[BookingModel]:
        """List bookings for a caregiver."""
        return await self.repo.list_for_caregiver(caregiver_id=caregiver_id, skip=skip, limit=limit)
