"""Shared pytest fixtures and test database setup for KidSync AI test suites."""

import os
from typing import AsyncGenerator
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.api.deps import get_db
from src.core.database import Base
from src.main import app

SHARED_TEST_DB = "test_kidsync_shared.db"
SHARED_DB_URL = f"sqlite+aiosqlite:///{SHARED_TEST_DB}"

shared_engine = create_async_engine(SHARED_DB_URL, echo=False)
shared_session_factory = async_sessionmaker(
    bind=shared_engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


async def shared_override_get_db() -> AsyncGenerator[AsyncSession, None]:
    async with shared_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


app.dependency_overrides[get_db] = shared_override_get_db


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_test_database():
    """Create all schema tables for the test session and clean up on completion."""
    async with shared_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with shared_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await shared_engine.dispose()
    if os.path.exists(SHARED_TEST_DB):
        try:
            os.remove(SHARED_TEST_DB)
        except OSError:
            pass


@pytest_asyncio.fixture
async def async_client():
    """Yield an authenticated/unauthenticated test AsyncClient."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
