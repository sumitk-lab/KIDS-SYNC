"""Booking and childcare session schemas with Pydantic v2 validation."""

import uuid
from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import Field, model_validator

from src.schemas.common import BookingStatusEnum, KidSyncBaseSchema


class BookingCreate(KidSyncBaseSchema):
    """Schema for requesting a new childcare booking."""

    caregiver_id: uuid.UUID
    start_time: datetime
    end_time: datetime
    special_instructions: Optional[str] = Field(default=None, max_length=1000)
    emergency_contact_override: Optional[Dict[str, Any]] = None

    @model_validator(mode="after")
    def validate_time_range(self) -> "BookingCreate":
        if self.end_time <= self.start_time:
            raise ValueError("end_time must be strictly after start_time.")
        return self


class BookingUpdate(KidSyncBaseSchema):
    """Schema for updating booking parameters."""

    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    status: Optional[BookingStatusEnum] = None
    special_instructions: Optional[str] = None
    cancellation_reason: Optional[str] = None

    @model_validator(mode="after")
    def validate_time_range_if_both_present(self) -> "BookingUpdate":
        if self.start_time and self.end_time and self.end_time <= self.start_time:
            raise ValueError("end_time must be strictly after start_time.")
        return self


class BookingStatusUpdate(KidSyncBaseSchema):
    """Schema for state transitions (Confirm, Cancel, Complete)."""

    status: BookingStatusEnum
    cancellation_reason: Optional[str] = Field(default=None, max_length=500)


class BookingResponse(KidSyncBaseSchema):
    """Schema returned for booking records."""

    id: uuid.UUID
    client_user_id: uuid.UUID
    caregiver_id: uuid.UUID
    start_time: datetime
    end_time: datetime
    status: BookingStatusEnum
    total_amount_cents: int
    currency: str
    special_instructions: Optional[str] = None
    emergency_contact_override: Optional[Dict[str, Any]] = None
    handoff_digest_id: Optional[uuid.UUID] = None
    cancellation_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime
