"""User repository implementation."""

from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.user import UserModel
from src.repositories.base import BaseRepository


class UserRepository(BaseRepository[UserModel]):
    """Repository handling database operations for users."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(UserModel, session)

    async def get_by_email(self, email: str) -> Optional[UserModel]:
        """Fetch user by case-insensitive email address."""
        result = await self.session.execute(
            select(UserModel).where(UserModel.email == email.lower().strip())
        )
        return result.scalars().first()

    async def list_by_role(self, role: str, skip: int = 0, limit: int = 50) -> List[UserModel]:
        """Fetch active users filtered by role."""
        result = await self.session.execute(
            select(UserModel)
            .where(UserModel.role == role, UserModel.is_active.is_(True))
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())
