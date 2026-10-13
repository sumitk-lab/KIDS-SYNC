"""NLP-driven End-of-Day (EOD) summary and transition briefing generator."""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.core.exceptions import ResourceNotFoundError
from src.models.booking import BookingModel
from src.models.caregiver import CaregiverModel
from src.models.telemetry import EODSummaryModel, TelemetryEventModel
from src.schemas.summary import EODMetrics, EODSummaryResponse
from src.services.audit_service import AuditService


class NLPSummaryService:
    """Service synthesizing throughout-the-day telemetry events into a structured EOD digest."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.audit_service = AuditService(session)

    async def generate_eod_summary(
        self,
        booking_id: uuid.UUID,
        child_name: str = "Child",
        actor_id: Optional[uuid.UUID] = None,
        client_ip: Optional[str] = None,
    ) -> EODSummaryModel:
        """Analyze session telemetry events and generate an NLP transition digest."""
        # 1. Fetch booking with telemetry events
        result = await self.session.execute(
            select(BookingModel)
            .where(BookingModel.id == booking_id)
            .options(
                selectinload(BookingModel.telemetry_events),
                selectinload(BookingModel.caregiver).selectinload(CaregiverModel.user),
            )
        )
        booking = result.scalars().first()
        if not booking:
            raise ResourceNotFoundError("Booking", booking_id)

        events: List[TelemetryEventModel] = booking.telemetry_events

        # 2. Compute aggregate metrics
        sleep_minutes = 0
        meal_percentages: List[float] = []
        meds_count = 0
        mood_scores: List[float] = []
        incident_count = 0
        highlights: List[str] = []
        action_items: List[str] = []

        for ev in events:
            ev_type = ev.event_type
            p = ev.payload or {}

            if ev_type == "NAP":
                duration = int(p.get("duration_minutes", 60))
                sleep_minutes += duration
                quality = p.get("quality", "restful")
                highlights.append(f"Sleep: {duration}m nap ({quality}).")

            elif ev_type == "MEAL":
                pct = float(p.get("percentage_eaten", 100.0))
                meal_percentages.append(pct)
                meal_name = p.get("meal_name", "Meal")
                highlights.append(f"Nutrition: {meal_name} consumed ({int(pct)}%).")

            elif ev_type == "MEDICATION":
                meds_count += 1
                med_name = p.get("medication_name", "Prescribed dose")
                dose = p.get("dose", "")
                time_str = ev.timestamp.strftime("%I:%M %p")
                highlights.append(f"Medication: {med_name} {dose} verified at {time_str}.")

            elif ev_type == "MOOD":
                mood_val = float(p.get("score", 5.0))
                mood_scores.append(mood_val)

            elif ev_type in ["INCIDENT", "ALERT"]:
                incident_count += 1
                desc = p.get("description", ev.notes or "Logged incident")
                highlights.append(f"Alert: {desc}")
                action_items.append(f"Review session incident note: {desc}")

            elif ev_type == "ACTIVITY":
                activity_name = p.get("name", "Outdoor play")
                highlights.append(f"Activity: {activity_name}.")

        avg_meal_pct = sum(meal_percentages) / len(meal_percentages) if meal_percentages else 100.0
        avg_mood = sum(mood_scores) / len(mood_scores) if mood_scores else 5.0

        if not action_items:
            action_items.append(f"All routines completed. Prepare clothing and water for tomorrow.")

        # 3. NLP Synthesis Narrative
        narrative_parts = []
        caregiver_name = "Caregiver"
        if booking.caregiver and booking.caregiver.user:
            caregiver_name = booking.caregiver.user.first_name

        narrative_parts.append(
            f"Care session for {child_name} was conducted by {caregiver_name}."
        )

        if incident_count == 0:
            narrative_parts.append(
                f"Overall, the day was peaceful and routine. {child_name} maintained an average mood of {avg_mood:.1f}/5.0."
            )
        else:
            narrative_parts.append(
                f"A safety or behavioral alert was recorded during the session. Please review the highlighted action items."
            )

        if sleep_minutes > 0:
            narrative_parts.append(
                f"{child_name} completed {sleep_minutes} minutes of nap time."
            )

        if meds_count > 0:
            narrative_parts.append(
                f"All {meds_count} scheduled medication dose(s) were successfully administered and photo-verified."
            )

        if avg_meal_pct < 60.0:
            narrative_parts.append(
                f"Appetite was lighter than usual (average {int(avg_meal_pct)}% eaten)."
            )
            action_items.append("Offer a nutritious evening snack.")
        else:
            narrative_parts.append(
                f"Appetite was strong with an average meal completion of {int(avg_meal_pct)}%."
            )

        summary_text = " ".join(narrative_parts)

        # 4. Check if summary already exists for this booking
        existing_res = await self.session.execute(
            select(EODSummaryModel).where(EODSummaryModel.booking_id == booking_id)
        )
        existing_summary = existing_res.scalars().first()

        now = datetime.now(timezone.utc)
        metrics_dict = {
            "total_sleep_minutes": sleep_minutes,
            "meal_completion_pct": round(avg_meal_pct, 1),
            "medications_given_count": meds_count,
            "average_mood": round(avg_mood, 1),
            "incident_count": incident_count,
        }

        if existing_summary:
            existing_summary.summary_text = summary_text
            existing_summary.highlights = highlights
            existing_summary.metrics = metrics_dict
            existing_summary.action_items = action_items
            existing_summary.generated_at = now
            summary_model = existing_summary
        else:
            summary_model = EODSummaryModel(
                booking_id=booking_id,
                summary_text=summary_text,
                highlights=highlights,
                metrics=metrics_dict,
                action_items=action_items,
                generated_at=now,
            )
            self.session.add(summary_model)

        await self.session.flush()

        # 5. Record event in cryptographic audit ledger
        await self.audit_service.log_event(
            actor_id=actor_id or booking.client_user_id,
            target_entity="eod_summaries",
            entity_id=summary_model.id,
            event_type="EOD_SUMMARY_GENERATED",
            payload_snapshot={
                "booking_id": str(booking_id),
                "metrics": metrics_dict,
                "action_items_count": len(action_items),
            },
            client_ip=client_ip,
        )

        return summary_model

    async def get_summary_by_booking(self, booking_id: uuid.UUID) -> EODSummaryModel:
        """Fetch existing EOD summary for a booking."""
        res = await self.session.execute(
            select(EODSummaryModel).where(EODSummaryModel.booking_id == booking_id)
        )
        summary = res.scalars().first()
        if not summary:
            raise ResourceNotFoundError("EODSummary", booking_id)
        return summary
