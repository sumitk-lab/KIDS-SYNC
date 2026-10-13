"""Caregiver management and assignment service."""

import uuid
from typing import List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import ConflictError, ResourceNotFoundError
from src.models.caregiver import CaregiverAssignmentModel, CaregiverModel
from src.repositories.caregiver_repo import CaregiverRepository
from src.repositories.user_repo import UserRepository
from src.schemas.caregiver import (
    CaregiverAssignmentCreate,
    CaregiverCreate,
    CaregiverUpdate,
)
from src.services.audit_service import AuditService


class CaregiverService:
    """Service handling caregiver profiles, vetting status, and delegation assignments."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = CaregiverRepository(session)
        self.user_repo = UserRepository(session)
        self.audit_service = AuditService(session)

    async def create_caregiver_profile(
        self,
        data: CaregiverCreate,
        actor_id: uuid.UUID,
        client_ip: Optional[str] = None,
    ) -> CaregiverModel:
        """Create a caregiver profile linked to an existing user."""
        # 1. Verify user exists
        user = await self.user_repo.get_by_id(data.user_id)
        if not user:
            raise ResourceNotFoundError("User", data.user_id)

        # 2. Check if caregiver profile already exists
        existing = await self.repo.get_by_user_id(data.user_id)
        if existing:
            raise ConflictError("Caregiver profile already exists for this user account.")

        caregiver = CaregiverModel(
            user_id=data.user_id,
            bio=data.bio,
            years_of_experience=data.years_of_experience,
            hourly_rate_cents=data.hourly_rate_cents,
            currency=data.currency,
            specialties=data.specialties,
            certifications=data.certifications,
            emergency_phone=data.emergency_phone,
            is_available=data.is_available,
            background_check_status="PENDING",
        )
        created = await self.repo.create(caregiver)

        # 3. Log audit event
        await self.audit_service.log_event(
            actor_id=actor_id,
            target_entity="caregivers",
            entity_id=created.id,
            event_type="CAREGIVER_PROFILE_CREATED",
            payload_snapshot={
                "user_id": str(created.user_id),
                "hourly_rate_cents": created.hourly_rate_cents,
                "specialties": created.specialties,
            },
            client_ip=client_ip,
        )
        return created

    async def get_by_id(self, caregiver_id: uuid.UUID) -> CaregiverModel:
        """Fetch caregiver by ID with user relation."""
        caregiver = await self.repo.get_with_user(caregiver_id)
        if not caregiver:
            raise ResourceNotFoundError("Caregiver", caregiver_id)
        return caregiver

    async def update_profile(
        self,
        caregiver_id: uuid.UUID,
        data: CaregiverUpdate,
        actor_id: uuid.UUID,
        client_ip: Optional[str] = None,
    ) -> CaregiverModel:
        """Update caregiver profile fields and record audit trail."""
        caregiver = await self.get_by_id(caregiver_id)

        update_dict = data.model_dump(exclude_unset=True)
        if "background_check_status" in update_dict and update_dict["background_check_status"]:
            update_dict["background_check_status"] = update_dict["background_check_status"].value

        for key, value in update_dict.items():
            setattr(caregiver, key, value)

        await self.session.flush()

        await self.audit_service.log_event(
            actor_id=actor_id,
            target_entity="caregivers",
            entity_id=caregiver.id,
            event_type="CAREGIVER_PROFILE_UPDATED",
            payload_snapshot=update_dict,
            client_ip=client_ip,
        )
        return caregiver

    async def assign_caregiver(
        self,
        assigned_by_user_id: uuid.UUID,
        data: CaregiverAssignmentCreate,
        client_ip: Optional[str] = None,
    ) -> CaregiverAssignmentModel:
        """Assign caregiver to a family circle with delegated permissions."""
        # Verify caregiver exists
        caregiver = await self.get_by_id(data.caregiver_id)

        # Check existing assignment
        existing = await self.repo.get_assignment(
            caregiver_id=data.caregiver_id,
            assigned_by_user_id=assigned_by_user_id,
        )
        if existing:
            raise ConflictError("Caregiver is already assigned to this family circle.")

        assignment = CaregiverAssignmentModel(
            caregiver_id=data.caregiver_id,
            assigned_by_user_id=assigned_by_user_id,
            role_type=data.role_type.value,
            can_view_health=data.can_view_health,
            can_view_schedule=data.can_view_schedule,
            can_view_financials=data.can_view_financials,
            can_administer_meds=data.can_administer_meds,
        )
        created = await self.repo.create_assignment(assignment)

        # Audit assignment
        await self.audit_service.log_event(
            actor_id=assigned_by_user_id,
            target_entity="caregiver_assignments",
            entity_id=created.id,
            event_type="CAREGIVER_ASSIGNED_TO_FAMILY",
            payload_snapshot={
                "caregiver_id": str(created.caregiver_id),
                "role_type": created.role_type,
                "can_view_health": created.can_view_health,
                "can_view_financials": created.can_view_financials,
            },
            client_ip=client_ip,
        )
        return created

    async def list_available(
        self,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[CaregiverModel], int]:
        """List available, verified caregivers."""
        items = await self.repo.list_available(skip=skip, limit=limit)
        total = await self.repo.count()
        return items, total
