"""Caregiver repository implementation."""

import uuid
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models.caregiver import CaregiverAssignmentModel, CaregiverModel
from src.repositories.base import BaseRepository


class CaregiverRepository(BaseRepository[CaregiverModel]):
    """Repository handling database operations for caregivers and assignments."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(CaregiverModel, session)

    async def get_by_user_id(self, user_id: uuid.UUID) -> Optional[CaregiverModel]:
        """Fetch caregiver profile by user ID with eager-loaded user relation."""
        result = await self.session.execute(
            select(CaregiverModel)
            .where(CaregiverModel.user_id == user_id)
            .options(selectinload(CaregiverModel.user))
        )
        return result.scalars().first()

    async def get_with_user(self, caregiver_id: uuid.UUID) -> Optional[CaregiverModel]:
        """Fetch caregiver by ID with eager user details."""
        result = await self.session.execute(
            select(CaregiverModel)
            .where(CaregiverModel.id == caregiver_id)
            .options(selectinload(CaregiverModel.user))
        )
        return result.scalars().first()

    async def list_available(
        self,
        skip: int = 0,
        limit: int = 50,
    ) -> List[CaregiverModel]:
        """Fetch caregivers that are currently available and passed background check."""
        result = await self.session.execute(
            select(CaregiverModel)
            .where(
                CaregiverModel.is_available.is_(True),
                CaregiverModel.background_check_status == "PASSED",
            )
            .options(selectinload(CaregiverModel.user))
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_assignment(
        self,
        caregiver_id: uuid.UUID,
        assigned_by_user_id: uuid.UUID,
    ) -> Optional[CaregiverAssignmentModel]:
        """Fetch assignment relationship between caregiver and family guardian."""
        result = await self.session.execute(
            select(CaregiverAssignmentModel).where(
                CaregiverAssignmentModel.caregiver_id == caregiver_id,
                CaregiverAssignmentModel.assigned_by_user_id == assigned_by_user_id,
            )
        )
        return result.scalars().first()

    async def create_assignment(
        self,
        assignment: CaregiverAssignmentModel,
    ) -> CaregiverAssignmentModel:
        """Create or persist a caregiver delegation assignment."""
        self.session.add(assignment)
        await self.session.flush()
        return assignment
