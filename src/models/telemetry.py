"""TelemetryEvent and EODSummary SQLAlchemy models."""

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from sqlalchemy import Float, ForeignKey, String, Text, JSON, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import Base
from src.models.base import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from src.models.booking import BookingModel
    from src.models.caregiver import CaregiverModel


class TelemetryEventModel(Base, UUIDPrimaryKeyMixin):
    """
    Real-time telemetry event emitted during childcare session
    (e.g., CHECK_IN, MEAL, NAP, MEDICATION, MOOD, ACTIVITY, INCIDENT, CHECK_OUT).
    """

    __tablename__ = "telemetry_events"

    booking_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("bookings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    caregiver_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("caregivers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_type: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
        index=True,
    )
    payload: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    battery_level: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )

    # Relationships
    booking: Mapped["BookingModel"] = relationship("BookingModel", back_populates="telemetry_events")
    caregiver: Mapped["CaregiverModel"] = relationship("CaregiverModel")


class EODSummaryModel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Synthesized NLP End-of-Day transition summary and handoff report.
    """

    __tablename__ = "eod_summaries"

    booking_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("bookings.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    summary_text: Mapped[str] = mapped_column(Text, nullable=False)
    highlights: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    metrics: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    action_items: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    acknowledged_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    booking: Mapped["BookingModel"] = relationship("BookingModel", back_populates="eod_summary")
