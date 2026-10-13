"""NLP End-of-Day Summary and transition briefing schemas."""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import Field

from src.schemas.common import KidSyncBaseSchema


class EODMetrics(KidSyncBaseSchema):
    """Structured metrics calculated from daily telemetry events."""

    total_sleep_minutes: int = Field(default=0, ge=0)
    meal_completion_pct: float = Field(default=100.0, ge=0.0, le=100.0)
    medications_given_count: int = Field(default=0, ge=0)
    average_mood: float = Field(default=5.0, ge=1.0, le=5.0)
    incident_count: int = Field(default=0, ge=0)


class EODSummaryGenerateRequest(KidSyncBaseSchema):
    """Request schema to trigger NLP EOD digest synthesis."""

    booking_id: uuid.UUID
    child_name: Optional[str] = "Child"


class EODSummaryResponse(KidSyncBaseSchema):
    """Schema for synthesized transition report and EOD briefing."""

    id: uuid.UUID
    booking_id: uuid.UUID
    summary_text: str
    highlights: List[str]
    metrics: EODMetrics
    action_items: List[str]
    generated_at: datetime
    acknowledged_at: Optional[datetime] = None
