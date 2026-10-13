"""Caregiver and CaregiverAssignment SQLAlchemy models."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text, JSON, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import Base
from src.models.base import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from src.models.user import UserModel
    from src.models.booking import BookingModel


class CaregiverModel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Caregiver profile model linked to a user account."""

    __tablename__ = "caregivers"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    bio: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    years_of_experience: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    hourly_rate_cents: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    specialties: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    certifications: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    background_check_status: Mapped[str] = mapped_column(
        String(30),
        default="PENDING",
        nullable=False,
        index=True,
    )
    background_checked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    emergency_phone: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    is_available: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    rating_average: Mapped[float] = mapped_column(Float, default=5.0, nullable=False)
    total_reviews_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Relationships
    user: Mapped["UserModel"] = relationship("UserModel", back_populates="caregiver_profile")
    assignments: Mapped[List["CaregiverAssignmentModel"]] = relationship(
        "CaregiverAssignmentModel",
        back_populates="caregiver",
        cascade="all, delete-orphan",
    )
    bookings: Mapped[List["BookingModel"]] = relationship(
        "BookingModel",
        back_populates="caregiver",
    )


class CaregiverAssignmentModel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """RBAC and delegation assignment linking caregivers to family guardians."""

    __tablename__ = "caregiver_assignments"

    caregiver_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("caregivers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    assigned_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role_type: Mapped[str] = mapped_column(
        String(30),
        default="CARE_PROVIDER",
        nullable=False,
    )
    can_view_health: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    can_view_schedule: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    can_view_financials: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    can_administer_meds: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    caregiver: Mapped["CaregiverModel"] = relationship("CaregiverModel", back_populates="assignments")
    assigned_by_user: Mapped["UserModel"] = relationship("UserModel", back_populates="created_assignments")
