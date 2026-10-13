import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Integer, String, Text, JSON, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import Base
from src.models.base import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from src.models.user import UserModel
    from src.models.caregiver import CaregiverModel
    from src.models.telemetry import TelemetryEventModel, EODSummaryModel


class BookingModel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Childcare session / booking request model."""

    __tablename__ = "bookings"
    __table_args__ = (
        CheckConstraint("end_time > start_time", name="chk_booking_time_range"),
    )

    client_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    caregiver_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("caregivers.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    start_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    end_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(30),
        default="PENDING",
        nullable=False,
        index=True,
    )
    total_amount_cents: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    special_instructions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    emergency_contact_override: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    handoff_digest_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    cancellation_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Automated Backup Caregiver Fallback Fields
    is_fallback: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    backup_caregiver_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    fallback_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    fallback_status: Mapped[str] = mapped_column(String(30), default="NONE", nullable=False)

    # Relationships
    client_user: Mapped["UserModel"] = relationship("UserModel", back_populates="bookings_as_client")
    caregiver: Mapped["CaregiverModel"] = relationship("CaregiverModel", back_populates="bookings")
    telemetry_events: Mapped[List["TelemetryEventModel"]] = relationship(
        "TelemetryEventModel",
        back_populates="booking",
        cascade="all, delete-orphan",
    )
    eod_summary: Mapped[Optional["EODSummaryModel"]] = relationship(
        "EODSummaryModel",
        back_populates="booking",
        uselist=False,
        cascade="all, delete-orphan",
    )
