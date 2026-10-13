"""API v1 master router aggregating auth, users, caregivers, bookings, and audit endpoints."""

from fastapi import APIRouter

from src.api.v1.auth import router as auth_router
from src.api.v1.users import router as users_router
from src.api.v1.caregivers import router as caregivers_router
from src.api.v1.bookings import router as bookings_router
from src.api.v1.audit import router as audit_router
from src.api.v1.matching import router as matching_router
from src.api.v1.telemetry import router as telemetry_router
from src.api.v1.summary import router as summary_router
from src.api.v1.fallback import router as fallback_router

api_v1_router = APIRouter()

api_v1_router.include_router(auth_router)
api_v1_router.include_router(users_router)
api_v1_router.include_router(caregivers_router)
api_v1_router.include_router(bookings_router)
api_v1_router.include_router(audit_router)
api_v1_router.include_router(matching_router)
api_v1_router.include_router(telemetry_router)
api_v1_router.include_router(summary_router)
api_v1_router.include_router(fallback_router)
