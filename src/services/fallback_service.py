"""Automated backup caregiver fallback orchestration service."""

import uuid
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.core.exceptions import ConflictError, ResourceNotFoundError
from src.ml.ranking_service import AutonomousMatchingService
from src.models.booking import BookingModel
from src.models.caregiver import CaregiverModel
from src.schemas.fallback import (
    BackupCandidateOffer,
    BackupFallbackWorkflowResponse,
    BackupTriggerRequest,
)
from src.schemas.matching import CaregiverMatchRequest
from src.services.audit_service import AuditService
from src.services.telemetry_manager import connection_manager


class BackupFallbackService:
    """Orchestrates automated emergency backup caregiver ranking, alert dispatch, and reassignment."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.audit_service = AuditService(session)
        self.matching_service = AutonomousMatchingService(session)

    async def execute_fallback_workflow(
        self,
        request: BackupTriggerRequest,
        actor_id: uuid.UUID,
        client_ip: Optional[str] = None,
    ) -> BackupFallbackWorkflowResponse:
        """
        Execute automated backup caregiver fallback pipeline:
        1. Validate booking state.
        2. Execute Two-Tower matching & Dynamic Trust scoring to locate replacement candidates.
        3. Exclude the original caregiver.
        4. If auto_assign is True, reassign the booking to the top-ranked vetted backup.
        5. Record the fallback in the cryptographic audit trail and broadcast alert via WebSockets.
        """
        # 1. Fetch booking with original caregiver details
        result = await self.session.execute(
            select(BookingModel)
            .where(BookingModel.id == request.booking_id)
            .options(
                selectinload(BookingModel.caregiver).selectinload(CaregiverModel.user),
                selectinload(BookingModel.client_user),
            )
        )
        booking = result.scalars().first()
        if not booking:
            raise ResourceNotFoundError("Booking", request.booking_id)

        if booking.status in ["COMPLETED", "CANCELLED", "REJECTED"]:
            raise ConflictError(f"Cannot trigger backup fallback on booking with terminal status '{booking.status}'.")

        original_caregiver_id = booking.caregiver_id
        duration_hours = max(1.0, (booking.end_time - booking.start_time).total_seconds() / 3600.0)

        # 2. Query Autonomous Matching pipeline for high-trust replacements
        match_request = CaregiverMatchRequest(
            child_age_years=3.0,
            has_special_needs=False,
            required_specialties=["INFANT_CARE", "FIRST_AID"],
            max_hourly_rate_cents=int(booking.total_amount_cents / duration_hours * 1.3),  # Allow 30% flex budget
            session_duration_hours=duration_hours,
            min_trust_score=50.0,
            top_k=10,
        )

        match_response = await self.matching_service.match_and_rank_caregivers(match_request)

        # 3. Filter out original caregiver
        replacement_candidates: List[BackupCandidateOffer] = []
        for candidate in match_response.matched_candidates:
            if candidate.caregiver_id != original_caregiver_id:
                replacement_candidates.append(
                    BackupCandidateOffer(
                        caregiver_id=candidate.caregiver_id,
                        name=f"{candidate.first_name} {candidate.last_name}".strip(),
                        trust_score=candidate.trust_breakdown.overall_trust_score,
                        match_score=candidate.match_score,
                        hourly_rate_cents=candidate.hourly_rate_cents,
                        specialties=candidate.specialties,
                        offer_status="OFFERED",
                    )
                )

        if not replacement_candidates:
            booking.fallback_status = "MANUAL_REVIEW_REQUIRED"
            booking.fallback_reason = request.reason
            await self.session.flush()

            # Audit failure to locate automatic backup
            await self.audit_service.log_event(
                actor_id=actor_id,
                target_entity="bookings",
                entity_id=booking.id,
                event_type="BACKUP_FALLBACK_FAILED_NO_CANDIDATES",
                payload_snapshot={
                    "original_caregiver_id": str(original_caregiver_id),
                    "reason": request.reason,
                },
                client_ip=client_ip,
            )

            return BackupFallbackWorkflowResponse(
                booking_id=booking.id,
                status="MANUAL_REVIEW_REQUIRED",
                original_caregiver_id=original_caregiver_id,
                backup_caregiver_id=None,
                assigned_caregiver_name=None,
                fallback_reason=request.reason,
                ranked_backup_candidates=[],
                message="No eligible backup caregivers met the trust criteria. Alerted emergency escalation queue.",
            )

        top_backup = replacement_candidates[0]

        # 4. Reassign if auto_assign is True
        assigned_name = None
        if request.auto_assign:
            booking.backup_caregiver_id = original_caregiver_id
            booking.caregiver_id = top_backup.caregiver_id
            booking.is_fallback = True
            booking.fallback_reason = request.reason
            booking.fallback_status = "BACKUP_ASSIGNED"
            top_backup.offer_status = "ACCEPTED"
            assigned_name = top_backup.name

            await self.session.flush()

            # 5. Record reassignment in cryptographic audit trail
            await self.audit_service.log_event(
                actor_id=actor_id,
                target_entity="bookings",
                entity_id=booking.id,
                event_type="BACKUP_CAREGIVER_ASSIGNED",
                payload_snapshot={
                    "original_caregiver_id": str(original_caregiver_id),
                    "new_backup_caregiver_id": str(top_backup.caregiver_id),
                    "assigned_caregiver_name": assigned_name,
                    "trust_score": top_backup.trust_score,
                    "match_score": top_backup.match_score,
                    "reason": request.reason,
                },
                client_ip=client_ip,
            )

            # 6. Broadcast backup alert via WebSocket channel
            await connection_manager.broadcast_to_booking(
                str(booking.id),
                {
                    "event": "telemetry.backup_assigned",
                    "booking_id": str(booking.id),
                    "data": {
                        "previous_caregiver_id": str(original_caregiver_id),
                        "assigned_caregiver_id": str(top_backup.caregiver_id),
                        "assigned_caregiver_name": assigned_name,
                        "trust_score": top_backup.trust_score,
                        "fallback_reason": request.reason,
                    },
                },
            )

            status_text = "BACKUP_ASSIGNED"
            msg = f"Booking automatically reassigned to verified backup caregiver {assigned_name} (Trust: {top_backup.trust_score})."
        else:
            booking.fallback_status = "TRIGGERED"
            booking.fallback_reason = request.reason
            await self.session.flush()
            status_text = "FALLBACK_TRIGGERED"
            msg = f"Located {len(replacement_candidates)} qualified backup candidates awaiting guardian selection."

        return BackupFallbackWorkflowResponse(
            booking_id=booking.id,
            status=status_text,
            original_caregiver_id=original_caregiver_id,
            backup_caregiver_id=top_backup.caregiver_id if request.auto_assign else None,
            assigned_caregiver_name=assigned_name,
            fallback_reason=request.reason,
            ranked_backup_candidates=replacement_candidates,
            message=msg,
        )
