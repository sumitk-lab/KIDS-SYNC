"""Real-time WebSocket and telemetry API endpoints."""

import uuid
from typing import List
from fastapi import APIRouter, Depends, Request, WebSocket, WebSocketDisconnect, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_client_ip, get_current_user, get_db
from src.models.user import UserModel
from src.schemas.common import ApiResponse
from src.schemas.telemetry import TelemetryEventCreate, TelemetryEventResponse
from src.services.telemetry_manager import TelemetryService, connection_manager

router = APIRouter(prefix="/telemetry", tags=["Real-Time Telemetry & Tracking"])


@router.websocket("/ws/{booking_id}")
async def websocket_telemetry_stream(
    websocket: WebSocket,
    booking_id: str,
) -> None:
    """
    Real-Time WebSocket communication channel for live childcare session tracking.
    Caregivers and family guardians subscribe to real-time status updates,
    check-in pings, activity events, and emergency alerts.
    """
    await connection_manager.connect(booking_id, websocket)
    try:
        while True:
            # Receive client ping or heartbeat frames
            data = await websocket.receive_text()
            # Echo heartbeat acknowledgment frame
            await websocket.send_json({
                "event": "telemetry.pong",
                "booking_id": booking_id,
                "ack": True,
            })
    except WebSocketDisconnect:
        connection_manager.disconnect(booking_id, websocket)
    except Exception:
        connection_manager.disconnect(booking_id, websocket)


@router.post(
    "/events",
    response_model=ApiResponse[TelemetryEventResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Record a real-time telemetry event (Check-in, Nap, Meal, Med, Mood)",
)
async def create_telemetry_event(
    event_data: TelemetryEventCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> ApiResponse[TelemetryEventResponse]:
    """Persist session activity and broadcast to all connected WebSocket subscribers."""
    client_ip = get_client_ip(request)
    service = TelemetryService(db)
    telemetry_event = await service.record_telemetry_event(
        caregiver_id=current_user.id,
        event_data=event_data,
        client_ip=client_ip,
    )
    return ApiResponse(
        success=True,
        message=f"Telemetry event {event_data.event_type.value} recorded and broadcasted.",
        data=TelemetryEventResponse.model_validate(telemetry_event),
    )


@router.get(
    "/events/{booking_id}",
    response_model=ApiResponse[List[TelemetryEventResponse]],
    summary="List all telemetry events for a childcare session",
)
async def list_telemetry_events(
    booking_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: UserModel = Depends(get_current_user),
) -> ApiResponse[List[TelemetryEventResponse]]:
    """Retrieve full chronological telemetry logs for a session."""
    service = TelemetryService(db)
    events = await service.list_events_for_booking(booking_id)
    dtos = [TelemetryEventResponse.model_validate(e) for e in events]
    return ApiResponse(
        success=True,
        message=f"Retrieved {len(dtos)} telemetry events.",
        data=dtos,
    )
