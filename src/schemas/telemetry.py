"""Real-time telemetry and WebSocket event schemas."""

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional
from pydantic import Field

from src.schemas.common import KidSyncBaseSchema


class TelemetryEventType(str, Enum):
    CHECK_IN = "CHECK_IN"
    CHECK_OUT = "CHECK_OUT"
    MEAL = "MEAL"
    NAP = "NAP"
    MEDICATION = "MEDICATION"
    MOOD = "MOOD"
    ACTIVITY = "ACTIVITY"
    INCIDENT = "INCIDENT"
    HEARTBEAT = "HEARTBEAT"
    ALERT = "ALERT"


class TelemetryEventCreate(KidSyncBaseSchema):
    """Schema for emitting a real-time tracking event."""

    booking_id: uuid.UUID
    event_type: TelemetryEventType
    payload: Dict[str, Any] = Field(default_factory=dict)
    notes: Optional[str] = Field(default=None, max_length=1000)
    battery_level: Optional[float] = Field(default=None, ge=0.0, le=100.0)


class TelemetryEventResponse(KidSyncBaseSchema):
    """Schema returned for a persisted telemetry event."""

    id: uuid.UUID
    booking_id: uuid.UUID
    caregiver_id: uuid.UUID
    event_type: str
    payload: Dict[str, Any]
    notes: Optional[str] = None
    battery_level: Optional[float] = None
    timestamp: datetime


class WebSocketEventEnvelope(KidSyncBaseSchema):
    """Envelope format for WebSocket stream frames."""

    event: str
    booking_id: str
    data: Dict[str, Any]
    timestamp: str
