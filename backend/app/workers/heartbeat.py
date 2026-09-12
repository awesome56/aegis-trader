"""Worker liveness heartbeat stored in Redis."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.core.config import Settings, get_settings

HEARTBEAT_KEY = "aegis:worker:heartbeat"


def _heartbeat_ttl(settings: Settings) -> int:
    return max(30, settings.WORKER_LOCK_TTL_SECONDS * 2)


async def write_heartbeat(redis: Any, settings: Settings | None = None) -> None:  # noqa: ANN401
    settings = settings or get_settings()
    await redis.set(
        HEARTBEAT_KEY, datetime.now(UTC).isoformat(), ex=_heartbeat_ttl(settings)
    )
