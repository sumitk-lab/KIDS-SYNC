"""Booking repository implementation."""

import uuid
from datetime import datetime
from typing import List, Optional
from sqlalchemy import and_, not_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models.booking import BookingModel
from src.repositories.base import BaseRepository


class BookingRepository(BaseRepository[BookingModel]):
    """Repository handling database operations for childcare bookings."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(BookingModel, session)

    async def get_with_details(self, booking_id: uuid.UUID) -> Optional[BookingModel]:
        """Fetch booking with client and caregiver relations eager loaded."""
        result = await self.session.execute(
            select(BookingModel)
            .where(BookingModel.id == booking_id)
            .options(
                selectinload(BookingModel.client_user),
                selectinload(BookingModel.caregiver),
            )
        )
        return result.scalars().first()

    async def check_overlap(
        self,
        caregiver_id: uuid.UUID,
        start_time: datetime,
        end_time: datetime,
        exclude_booking_id: Optional[uuid.UUID] = None,
    ) -> bool:
        """
        Check if caregiver already has an active or confirmed booking in the requested window.
        Overlap condition: (StartA < EndB) and (EndA > StartB)
        """
        query = select(BookingModel).where(
            BookingModel.caregiver_id == caregiver_id,
            BookingModel.status.in_(["PENDING", "CONFIRMED", "IN_PROGRESS"]),
            and_(
                BookingModel.start_time < end_time,
                BookingModel.end_time > start_time,
            ),
        )
        if exclude_booking_id:
            query = query.where(BookingModel.id != exclude_booking_id)

        result = await self.session.execute(query)
        return result.scalars().first() is not None

    async def list_for_client(
        self,
        client_user_id: uuid.UUID,
        skip: int = 0,
        limit: int = 50,
    ) -> List[BookingModel]:
        """Fetch all bookings created by a specific client/guardian."""
        result = await self.session.execute(
            select(BookingModel)
            .where(BookingModel.client_user_id == client_user_id)
            .order_by(BookingModel.start_time.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def list_for_caregiver(
        self,
        caregiver_id: uuid.UUID,
        skip: int = 0,
        limit: int = 50,
    ) -> List[BookingModel]:
        """Fetch all bookings scheduled for a specific caregiver."""
        result = await self.session.execute(
            select(BookingModel)
            .where(BookingModel.caregiver_id == caregiver_id)
            .order_by(BookingModel.start_time.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())
