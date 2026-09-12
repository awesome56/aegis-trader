"""Redis connection management (async)."""

from __future__ import annotations

from typing import Any

from redis.asyncio import Redis

from app.core.config import get_settings

_redis: Redis | None = None


def get_redis() -> Redis:
    global _redis
    if _redis is None:
        _redis = Redis.from_url(
            get_settings().REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
        )
    return _redis


async def check_redis() -> bool:
    """Return ``True`` when Redis responds to ``PING``."""
    try:
        client: Any = get_redis()
        return bool(await client.ping())
    except Exception:  # noqa: BLE001 - health check must never raise
        return False


async def close_redis() -> None:
    global _redis
    if _redis is not None:
        await _redis.aclose()
    _redis = None
