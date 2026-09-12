"""Pytest fixtures.

The suite runs against an isolated SQLite database so it needs no PostgreSQL or
Redis. Health checks therefore report Redis as unhealthy (expected).
"""

from __future__ import annotations

import os
import tempfile
from collections.abc import AsyncIterator

# Configure the environment BEFORE the app/settings are imported.
_TMPDIR = tempfile.mkdtemp(prefix="aegis-tests-")
os.environ.update(
    {
        "DATABASE_URL": f"sqlite+aiosqlite:///{_TMPDIR}/test.db",
        "ENVIRONMENT": "test",
        "DEBUG": "false",
        "LOG_LEVEL": "WARNING",
        "JWT_SECRET": "test-secret-value-that-is-long-enough-1234567890",
        "REDIS_URL": "redis://127.0.0.1:6399/0",
        "TRADING_MODE": "paper",
        "LIVE_TRADING_ENABLED": "false",
        "PAPER_INITIAL_BALANCE": "100000.00",
    }
)

import pytest_asyncio  # noqa: E402
from app.database.session import dispose_engine, get_engine  # noqa: E402
from app.main import create_app  # noqa: E402
from app.models import Base  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402


@pytest_asyncio.fixture(scope="session", autouse=True)
async def _database() -> AsyncIterator[None]:
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await dispose_engine()


@pytest_asyncio.fixture
async def client() -> AsyncIterator[AsyncClient]:
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as http:
        yield http


@pytest_asyncio.fixture
async def reset_users() -> AsyncIterator[None]:
    from app.database.session import get_session_factory
    from app.models.user import User, UserSession
    from sqlalchemy import delete

    factory = get_session_factory()
    async with factory() as session:
        await session.execute(delete(UserSession))
        await session.execute(delete(User))
        await session.commit()
    yield


@pytest_asyncio.fixture
async def db_session() -> AsyncIterator:
    from app.database.session import get_session_factory

    factory = get_session_factory()
    async with factory() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def authenticated_client(client: AsyncClient, reset_users: None) -> AsyncClient:
    """A client with a bootstrap account and an access token attached."""
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": "owner@example.com", "password": "supersecret12345"},
    )
    assert response.status_code == 201, response.text
    token = response.json()["tokens"]["access_token"]
    client.headers["Authorization"] = f"Bearer {token}"
    return client
