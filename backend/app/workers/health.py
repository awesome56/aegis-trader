"""Worker health: report heartbeat freshness for /health and /system/status."""

from __future__ import annotations

from datetime import UTC, datetime

from app.core.config import Settings, get_settings
from app.database.redis import check_redis, get_redis
from app.workers.heartbeat import HEARTBEAT_KEY, _heartbeat_ttl


async def worker_health(settings: Settings | None = None) -> tuple[str, str]:
    """Return ``(component_state, detail)`` for the worker.

    Never raises: health endpoints must degrade, not fail.
    """
    settings = settings or get_settings()
    if not settings.WORKER_ENABLED:
        return "not_configured", "worker disabled (WORKER_ENABLED=false)"
    if not await check_redis():
        return "degraded", "redis unavailable; worker liveness unknown"
    try:
        raw = await get_redis().get(HEARTBEAT_KEY)
    except Exception as exc:  # noqa: BLE001 - health must never raise
        return "degraded", f"redis error: {exc}"
    if not raw:
        return "unhealthy", "no worker heartbeat recorded"
    try:
        seen = datetime.fromisoformat(raw)
    except ValueError:
        return "unhealthy", "worker heartbeat is malformed"
    if seen.tzinfo is None:
        seen = seen.replace(tzinfo=UTC)
    age = (datetime.now(UTC) - seen).total_seconds()
    if age > _heartbeat_ttl(settings):
        return "unhealthy", f"worker heartbeat stale ({age:.0f}s)"
    return "healthy", f"worker heartbeat {age:.0f}s ago"
