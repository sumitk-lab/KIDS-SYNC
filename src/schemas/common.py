"""Common enums, base classes, and response envelopes for Pydantic v2."""

from enum import Enum
from typing import Generic, List, Optional, TypeVar
from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class UserRoleEnum(str, Enum):
    PRIMARY_GUARDIAN = "PRIMARY_GUARDIAN"
    EXTENDED_GUARDIAN = "EXTENDED_GUARDIAN"
    CARE_PROVIDER = "CARE_PROVIDER"
    OBSERVER = "OBSERVER"
    ADMIN = "ADMIN"


class BackgroundCheckStatusEnum(str, Enum):
    PENDING = "PENDING"
    PASSED = "PASSED"
    FAILED = "FAILED"
    EXPIRED = "EXPIRED"


class BookingStatusEnum(str, Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"


class KidSyncBaseSchema(BaseModel):
    """Base schema enforcing Pydantic v2 configuration."""

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        str_strip_whitespace=True,
    )


class ApiResponse(KidSyncBaseSchema, Generic[T]):
    """Standardized API response envelope."""

    success: bool = True
    message: str = "Operation completed successfully."
    data: Optional[T] = None


class PaginatedResponse(KidSyncBaseSchema, Generic[T]):
    """Standardized paginated list response."""

    items: List[T]
    total_count: int = Field(ge=0)
    page: int = Field(ge=1, default=1)
    page_size: int = Field(ge=1, le=100, default=20)
    has_next: bool = False
