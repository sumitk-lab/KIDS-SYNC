"""Caregiver and assignment schemas with Pydantic v2 validation."""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import Field

from src.schemas.common import BackgroundCheckStatusEnum, KidSyncBaseSchema, UserRoleEnum
from src.schemas.user import UserResponse


class CaregiverCreate(KidSyncBaseSchema):
    """Schema for registering a caregiver profile."""

    user_id: uuid.UUID
    bio: Optional[str] = Field(default=None, max_length=2000)
    years_of_experience: int = Field(default=0, ge=0, le=70)
    hourly_rate_cents: int = Field(default=0, ge=0)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    specialties: List[str] = Field(default_factory=list)
    certifications: List[Dict[str, Any]] = Field(default_factory=list)
    emergency_phone: Optional[str] = Field(default=None, max_length=30)
    is_available: bool = True


class CaregiverUpdate(KidSyncBaseSchema):
    """Schema for updating caregiver profile details."""

    bio: Optional[str] = Field(default=None, max_length=2000)
    years_of_experience: Optional[int] = Field(default=None, ge=0, le=70)
    hourly_rate_cents: Optional[int] = Field(default=None, ge=0)
    currency: Optional[str] = Field(default=None, min_length=3, max_length=3)
    specialties: Optional[List[str]] = None
    certifications: Optional[List[Dict[str, Any]]] = None
    background_check_status: Optional[BackgroundCheckStatusEnum] = None
    emergency_phone: Optional[str] = Field(default=None, max_length=30)
    is_available: Optional[bool] = None


class CaregiverResponse(KidSyncBaseSchema):
    """Schema for returning caregiver details."""

    id: uuid.UUID
    user_id: uuid.UUID
    bio: Optional[str] = None
    years_of_experience: int
    hourly_rate_cents: int
    currency: str
    specialties: List[str]
    certifications: List[Dict[str, Any]]
    background_check_status: BackgroundCheckStatusEnum
    background_checked_at: Optional[datetime] = None
    emergency_phone: Optional[str] = None
    is_available: bool
    rating_average: float
    total_reviews_count: int
    created_at: datetime
    updated_at: datetime
    user: Optional[UserResponse] = None


class CaregiverAssignmentCreate(KidSyncBaseSchema):
    """Schema for delegating care permissions to a caregiver."""

    caregiver_id: uuid.UUID
    role_type: UserRoleEnum = UserRoleEnum.CARE_PROVIDER
    can_view_health: bool = True
    can_view_schedule: bool = True
    can_view_financials: bool = False
    can_administer_meds: bool = True


class CaregiverAssignmentResponse(KidSyncBaseSchema):
    """Schema for returning caregiver assignment permissions."""

    id: uuid.UUID
    caregiver_id: uuid.UUID
    assigned_by_user_id: uuid.UUID
    role_type: UserRoleEnum
    can_view_health: bool
    can_view_schedule: bool
    can_view_financials: bool
    can_administer_meds: bool
    created_at: datetime
    updated_at: datetime
