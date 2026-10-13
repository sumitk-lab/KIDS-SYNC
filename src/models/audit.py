"""AuditLogEntry SQLAlchemy model for court-admissible cryptographic ledgers."""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict
from sqlalchemy import BigInteger, DateTime, Index, Integer, String, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class AuditLogEntryModel(Base):
    """
    Immutable, append-only court-admissible audit log entry.
    Implements SHA-256 cryptographic hash-chaining across entries.
    """

    __tablename__ = "audit_log_entries"
    __table_args__ = (
        Index("idx_audit_log_entity", "target_entity", "entity_id"),
        Index("idx_audit_log_actor_id", "actor_id"),
        Index("idx_audit_log_created_at", "created_at"),
        Index("idx_audit_log_entry_hash", "entry_hash"),
    )

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        primary_key=True,
        autoincrement=True,
    )
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    target_entity: Mapped[str] = mapped_column(String(60), nullable=False)
    event_type: Mapped[str] = mapped_column(String(60), nullable=False)
    actor_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    payload_snapshot: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    client_ip_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    prev_entry_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    entry_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
