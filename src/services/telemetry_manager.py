"""WebSocket connection manager and real-time telemetry service."""

import json
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set
from fastapi import WebSocket
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import ResourceNotFoundError, ValidationError
from src.models.booking import BookingModel
from src.models.caregiver import CaregiverModel
from src.models.telemetry import TelemetryEventModel
from src.schemas.telemetry import TelemetryEventCreate, TelemetryEventResponse, WebSocketEventEnvelope
from src.services.audit_service import AuditService


class ConnectionManager:
    """Manages active WebSocket connections grouped by booking_id."""

    def __init__(self) -> None:
        self.active_rooms: Dict[str, Set[WebSocket]] = defaultdict(set)

    async def connect(self, booking_id: str, websocket: WebSocket) -> None:
        """Accept WebSocket connection and register to booking room."""
        await websocket.accept()
        self.active_rooms[booking_id].add(websocket)

    def disconnect(self, booking_id: str, websocket: WebSocket) -> None:
        """Remove WebSocket connection from booking room."""
        if booking_id in self.active_rooms:
            self.active_rooms[booking_id].discard(websocket)
            if not self.active_rooms[booking_id]:
                del self.active_rooms[booking_id]

    async def broadcast_to_booking(self, booking_id: str, message: Dict[str, Any]) -> None:
        """Broadcast JSON message to all subscribers in booking room."""
        if booking_id not in self.active_rooms:
            return

        dead_connections: Set[WebSocket] = set()
        for connection in list(self.active_rooms[booking_id]):
            try:
                await connection.send_json(message)
            except Exception:
                dead_connections.add(connection)

        for dead in dead_connections:
            self.active_rooms[booking_id].discard(dead)


# Global singleton instance of connection manager
connection_manager = ConnectionManager()


class TelemetryService:
    """Service handling telemetry persistence, status transitions, and WebSocket broadcasts."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.audit_service = AuditService(session)

    async def record_telemetry_event(
        self,
        caregiver_id: uuid.UUID,
        event_data: TelemetryEventCreate,
        client_ip: Optional[str] = None,
    ) -> TelemetryEventModel:
        """Persist telemetry event, update booking state, and broadcast to WebSocket channel."""
        # 1. Verify booking
        booking_res = await self.session.execute(
            select(BookingModel).where(BookingModel.id == event_data.booking_id)
        )
        booking = booking_res.scalars().first()
        if not booking:
            raise ResourceNotFoundError("Booking", event_data.booking_id)

        # 2. Status state transitions based on event type
        now = datetime.now(timezone.utc)
        event_type = event_data.event_type.value

        if event_type == "CHECK_IN":
            if booking.status in ["PENDING", "CONFIRMED"]:
                booking.status = "IN_PROGRESS"
        elif event_type == "CHECK_OUT":
            if booking.status == "IN_PROGRESS":
                booking.status = "COMPLETED"

        # 3. Create Telemetry Model
        telemetry_event = TelemetryEventModel(
            booking_id=event_data.booking_id,
            caregiver_id=caregiver_id,
            event_type=event_type,
            payload=event_data.payload,
            notes=event_data.notes,
            battery_level=event_data.battery_level,
            timestamp=now,
        )
        self.session.add(telemetry_event)
        await self.session.flush()

        # 4. Record high-consequence events in cryptographic audit ledger
        if event_type in ["CHECK_IN", "CHECK_OUT", "MEDICATION", "INCIDENT", "ALERT"]:
            await self.audit_service.log_event(
                actor_id=caregiver_id,
                target_entity="telemetry_events",
                entity_id=telemetry_event.id,
                event_type=f"TELEMETRY_{event_type}",
                payload_snapshot={
                    "booking_id": str(booking.id),
                    "event_type": event_type,
                    "payload": event_data.payload,
                    "notes": event_data.notes,
                },
                client_ip=client_ip,
            )

        # 5. Broadcast to active WebSocket connections
        envelope = WebSocketEventEnvelope(
            event=f"telemetry.{event_type.lower()}",
            booking_id=str(booking.id),
            data={
                "event_id": str(telemetry_event.id),
                "caregiver_id": str(caregiver_id),
                "event_type": event_type,
                "payload": event_data.payload,
                "notes": event_data.notes,
                "battery_level": event_data.battery_level,
                "booking_status": booking.status,
            },
            timestamp=now.isoformat(),
        )
        await connection_manager.broadcast_to_booking(
            str(booking.id),
            envelope.model_dump(),
        )

        return telemetry_event

    async def list_events_for_booking(self, booking_id: uuid.UUID) -> List[TelemetryEventModel]:
        """Fetch all telemetry events for a specific childcare session."""
        result = await self.session.execute(
            select(TelemetryEventModel)
            .where(TelemetryEventModel.booking_id == booking_id)
            .order_by(TelemetryEventModel.timestamp.asc())
        )
        return list(result.scalars().all())
