"""User schemas with Pydantic v2 validation."""

import uuid
from datetime import datetime
from typing import Optional
from pydantic import EmailStr, Field

from src.schemas.common import KidSyncBaseSchema, UserRoleEnum


class UserCreate(KidSyncBaseSchema):
    """Schema for registering a new user."""

    email: EmailStr
    password: str = Field(min_length=8, max_length=128, description="Password must be at least 8 characters.")
    first_name: str = Field(min_length=1, max_length=60)
    last_name: str = Field(min_length=1, max_length=60)
    phone: Optional[str] = Field(default=None, max_length=30)
    avatar_url: Optional[str] = None
    role: UserRoleEnum = UserRoleEnum.PRIMARY_GUARDIAN


class UserUpdate(KidSyncBaseSchema):
    """Schema for updating an existing user's profile."""

    first_name: Optional[str] = Field(default=None, min_length=1, max_length=60)
    last_name: Optional[str] = Field(default=None, min_length=1, max_length=60)
    phone: Optional[str] = Field(default=None, max_length=30)
    avatar_url: Optional[str] = None
    role: Optional[UserRoleEnum] = None
    is_active: Optional[bool] = None


class UserResponse(KidSyncBaseSchema):
    """Schema returned to clients for user records (passwords excluded)."""

    id: uuid.UUID
    email: EmailStr
    first_name: str
    last_name: str
    phone: Optional[str] = None
    avatar_url: Optional[str] = None
    role: UserRoleEnum
    is_active: bool
    is_verified: bool
    created_at: datetime
    updated_at: datetime


class UserLogin(KidSyncBaseSchema):
    """Schema for email/password authentication."""

    email: EmailStr
    password: str = Field(min_length=1)


class TokenResponse(KidSyncBaseSchema):
    """Schema for JWT authentication tokens."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse
