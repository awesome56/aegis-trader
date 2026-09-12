"""Redis-backed mutual-exclusion lock for worker jobs.

Jobs may take longer than their schedule; a best-effort distributed lock keeps
runs from overlapping without requiring a separate scheduler. TTL bounds the
damage from a crashed worker holding the lock.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any, Protocol


class _LockRedis(Protocol):
    async def set(self, key: str, value: str, *, nx: bool = ..., px: int | None = ...) -> Any: ...
    async def get(self, key: str) -> Any: ...
    async def delete(self, key: str) -> Any: ...


class LockNotAcquiredError(RuntimeError):
    """Raised when a job cannot obtain its lock (another run is active)."""


def _as_text(value: Any) -> str | None:  # noqa: ANN401
    if value is None:
        return None
    return value.decode() if isinstance(value, bytes) else str(value)


@asynccontextmanager
async def redis_lock(
    redis: _LockRedis, key: str, *, ttl_seconds: int
) -> AsyncIterator[None]:
    """Acquire ``key`` or raise :class:`LockNotAcquiredError`; always release."""
    token = uuid.uuid4().hex
    acquired = await redis.set(key, token, nx=True, px=ttl_seconds * 1000)
    if not acquired:
        raise LockNotAcquiredError(f"lock {key} is held")
    try:
        yield
    finally:
        if _as_text(await redis.get(key)) == token:
            await redis.delete(key)
