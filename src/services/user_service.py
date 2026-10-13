"""User business logic service."""

import uuid
from typing import List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.core.exceptions import AuthenticationError, ConflictError, ResourceNotFoundError
from src.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
)
from src.models.user import UserModel
from src.repositories.user_repo import UserRepository
from src.schemas.user import TokenResponse, UserCreate, UserResponse, UserUpdate
from src.services.audit_service import AuditService


class UserService:
    """Service handling user account registration, authentication, and profile management."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = UserRepository(session)
        self.audit_service = AuditService(session)

    async def register_user(
        self,
        data: UserCreate,
        client_ip: Optional[str] = None,
    ) -> Tuple[UserModel, TokenResponse]:
        """Register a new user account, generate tokens, and write cryptographic audit record."""
        # Check duplicate email
        existing = await self.repo.get_by_email(data.email)
        if existing:
            raise ConflictError(f"User with email '{data.email}' already exists.")

        # Hash password & construct model
        hashed = hash_password(data.password)
        user = UserModel(
            email=data.email.lower().strip(),
            hashed_password=hashed,
            first_name=data.first_name.strip(),
            last_name=data.last_name.strip(),
            phone=data.phone,
            avatar_url=data.avatar_url,
            role=data.role.value,
            is_active=True,
            is_verified=False,
        )
        created_user = await self.repo.create(user)

        # Audit event
        await self.audit_service.log_event(
            actor_id=created_user.id,
            target_entity="users",
            entity_id=created_user.id,
            event_type="USER_REGISTERED",
            payload_snapshot={
                "email": created_user.email,
                "role": created_user.role,
                "first_name": created_user.first_name,
                "last_name": created_user.last_name,
            },
            client_ip=client_ip,
        )

        tokens = self._generate_tokens(created_user)
        return created_user, tokens

    async def authenticate(
        self,
        email: str,
        password: str,
        client_ip: Optional[str] = None,
    ) -> Tuple[UserModel, TokenResponse]:
        """Authenticate user by email and password."""
        user = await self.repo.get_by_email(email)
        if not user or not verify_password(password, user.hashed_password):
            raise AuthenticationError("Invalid email or password.")

        if not user.is_active:
            raise AuthenticationError("User account has been deactivated.")

        # Audit login
        await self.audit_service.log_event(
            actor_id=user.id,
            target_entity="users",
            entity_id=user.id,
            event_type="USER_AUTHENTICATED",
            payload_snapshot={"email": user.email},
            client_ip=client_ip,
        )

        tokens = self._generate_tokens(user)
        return user, tokens

    async def get_by_id(self, user_id: uuid.UUID) -> UserModel:
        """Fetch user by ID or raise ResourceNotFoundError."""
        user = await self.repo.get_by_id(user_id)
        if not user:
            raise ResourceNotFoundError("User", user_id)
        return user

    async def update_user(
        self,
        user_id: uuid.UUID,
        data: UserUpdate,
        actor_id: uuid.UUID,
        client_ip: Optional[str] = None,
    ) -> UserModel:
        """Update user profile fields and append to audit trail."""
        user = await self.get_by_id(user_id)

        update_dict = data.model_dump(exclude_unset=True)
        if "role" in update_dict and update_dict["role"]:
            update_dict["role"] = update_dict["role"].value

        for key, value in update_dict.items():
            setattr(user, key, value)

        await self.session.flush()

        await self.audit_service.log_event(
            actor_id=actor_id,
            target_entity="users",
            entity_id=user.id,
            event_type="USER_UPDATED",
            payload_snapshot=update_dict,
            client_ip=client_ip,
        )
        return user

    async def list_users(self, skip: int = 0, limit: int = 50) -> Tuple[List[UserModel], int]:
        """List active users with pagination."""
        items = await self.repo.list(skip=skip, limit=limit)
        total = await self.repo.count()
        return items, total

    def _generate_tokens(self, user: UserModel) -> TokenResponse:
        """Helper to create access and refresh tokens."""
        access_token = create_access_token(
            subject=str(user.id),
            role=user.role,
        )
        refresh_token = create_refresh_token(subject=str(user.id))
        user_dto = UserResponse.model_validate(user)
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=user_dto,
        )
