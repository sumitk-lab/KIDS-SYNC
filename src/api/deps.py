"""FastAPI dependency injections for database sessions, current user, and RBAC."""

import uuid
from typing import AsyncGenerator, Callable, List, Optional
from fastapi import Depends, Header, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db_session
from src.core.exceptions import AuthenticationError, AuthorizationError
from src.core.security import decode_token
from src.models.user import UserModel
from src.repositories.user_repo import UserRepository

bearer_scheme = HTTPBearer(auto_error=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for obtaining an asynchronous database session."""
    async for session in get_db_session():
        yield session


def get_client_ip(request: Request) -> str:
    """Extract client IP address from proxy headers or connection host."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip.strip()
    return request.client.host if request.client else "127.0.0.1"


async def get_current_user(
    auth: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> UserModel:
    """Dependency that authenticates the request via Bearer JWT and retrieves the UserModel."""
    if not auth or not auth.credentials:
        raise AuthenticationError("Bearer token is required.")

    payload = decode_token(auth.credentials)
    if payload.get("type") != "access":
        raise AuthenticationError("Invalid token type. Access token required.")

    user_id_str = payload.get("sub")
    if not user_id_str:
        raise AuthenticationError("Token payload missing subject identifier.")

    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        raise AuthenticationError("Malformed user identifier in token.")

    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(user_id)
    if not user:
        raise AuthenticationError("User associated with this token no longer exists.")

    if not user.is_active:
        raise AuthenticationError("User account is deactivated.")

    return user


def require_roles(*allowed_roles: str) -> Callable[[UserModel], UserModel]:
    """Factory dependency to enforce Role-Based Access Control (RBAC)."""

    async def role_checker(
        current_user: UserModel = Depends(get_current_user),
    ) -> UserModel:
        if current_user.role not in allowed_roles:
            raise AuthorizationError(
                f"Role '{current_user.role}' is not authorized to access this resource. "
                f"Required one of: {list(allowed_roles)}"
            )
        return current_user

    return role_checker
