"""User SQLAlchemy model."""

from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import Base
from src.models.base import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from src.models.caregiver import CaregiverModel, CaregiverAssignmentModel
    from src.models.booking import BookingModel


class UserModel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """User account model for parents, guardians, caregivers, and admins."""

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    first_name: Mapped[str] = mapped_column(String(60), nullable=False)
    last_name: Mapped[str] = mapped_column(String(60), nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    role: Mapped[str] = mapped_column(
        String(30),
        default="PRIMARY_GUARDIAN",
        nullable=False,
        index=True,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    caregiver_profile: Mapped[Optional["CaregiverModel"]] = relationship(
        "CaregiverModel",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
    bookings_as_client: Mapped[List["BookingModel"]] = relationship(
        "BookingModel",
        back_populates="client_user",
        cascade="all, delete-orphan",
    )
    created_assignments: Mapped[List["CaregiverAssignmentModel"]] = relationship(
        "CaregiverAssignmentModel",
        back_populates="assigned_by_user",
        cascade="all, delete-orphan",
    )

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"
