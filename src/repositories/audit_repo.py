"""Audit repository implementation for cryptographic ledger operations."""

import uuid
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.audit import AuditLogEntryModel
from src.repositories.base import BaseRepository

GENESIS_HASH = "0" * 64


class AuditRepository(BaseRepository[AuditLogEntryModel]):
    """Repository handling cryptographic audit log queries and appends."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(AuditLogEntryModel, session)

    async def get_latest_entry(self) -> Optional[AuditLogEntryModel]:
        """Fetch the most recent audit entry to extract its entry_hash as the next prev_entry_hash."""
        result = await self.session.execute(
            select(AuditLogEntryModel).order_by(AuditLogEntryModel.id.desc()).limit(1)
        )
        return result.scalars().first()

    async def list_for_entity(
        self,
        target_entity: str,
        entity_id: uuid.UUID,
        skip: int = 0,
        limit: int = 100,
    ) -> List[AuditLogEntryModel]:
        """Fetch audit trail for a specific entity ordered chronologically."""
        result = await self.session.execute(
            select(AuditLogEntryModel)
            .where(
                AuditLogEntryModel.target_entity == target_entity,
                AuditLogEntryModel.entity_id == entity_id,
            )
            .order_by(AuditLogEntryModel.id.asc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_all_ordered_by_id(
        self,
        from_id: int = 1,
        limit: int = 1000,
    ) -> List[AuditLogEntryModel]:
        """Fetch ordered batch of audit entries for chain verification."""
        result = await self.session.execute(
            select(AuditLogEntryModel)
            .where(AuditLogEntryModel.id >= from_id)
            .order_by(AuditLogEntryModel.id.asc())
            .limit(limit)
        )
        return list(result.scalars().all())
