"""Worker package tests (locks, schedules, health, jobs)."""

from __future__ import annotations

from typing import Any

import pytest
from app.core.config import get_settings
from app.workers.health import worker_health
from app.workers.heartbeat import HEARTBEAT_KEY
from app.workers.lock import LockNotAcquiredError, redis_lock
from app.workers.main import build_cron_jobs, minute_schedule, seconds_schedule


class FakeRedis:
    def __init__(self) -> None:
        self.store: dict[str, str] = {}

    async def set(
        self,
        key: str,
        value: str,
        *,
        nx: bool = False,
        px: int | None = None,
        ex: int | None = None,
    ) -> Any:  # noqa: ANN401
        if nx and key in self.store:
            return None
        self.store[key] = value
        return True

    async def get(self, key: str) -> str | None:
        return self.store.get(key)

    async def delete(self, key: str) -> int:
        return 1 if self.store.pop(key, None) is not None else 0


async def test_lock_is_exclusive_and_released() -> None:
    redis = FakeRedis()
    async with redis_lock(redis, "job", ttl_seconds=30):  # type: ignore[arg-type]
        with pytest.raises(LockNotAcquiredError):
            async with redis_lock(redis, "job", ttl_seconds=30):  # type: ignore[arg-type]
                pass
    # Released after the first run completes.
    async with redis_lock(redis, "job", ttl_seconds=30):  # type: ignore[arg-type]
        pass


def test_schedules() -> None:
    assert seconds_schedule(10) == {0, 10, 20, 30, 40, 50}
    assert minute_schedule(300) == {0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55}
    assert seconds_schedule(1000) == set(range(0, 60, 59))


def test_cron_jobs_built_from_settings() -> None:
    jobs = build_cron_jobs()
    assert len(jobs) == 3


async def test_worker_health_disabled() -> None:
    settings = get_settings().model_copy(update={"WORKER_ENABLED": False})
    state, detail = await worker_health(settings)
    assert state == "not_configured"
    assert "disabled" in detail


async def test_worker_health_without_redis_degrades() -> None:
    settings = get_settings().model_copy(update={"WORKER_ENABLED": True})
    state, _ = await worker_health(settings)
    assert state in {"degraded", "unhealthy"}


async def test_heartbeat_and_jobs_with_fake_redis() -> None:
    from app.workers.heartbeat import write_heartbeat
    from app.workers.jobs import monitor_open_orders, portfolio_snapshot

    settings = get_settings()
    settings = settings.model_copy(update={"WORKER_ENABLED": True})
    redis = FakeRedis()
    ctx: dict[str, Any] = {"redis": redis, "settings": settings}

    await write_heartbeat(redis, settings)
    assert HEARTBEAT_KEY in redis.store

    snapshot = await portfolio_snapshot(ctx)
    assert snapshot["job"] == "portfolio_snapshot"

    monitor = await monitor_open_orders(ctx)
    assert monitor["job"] == "open_order_monitor"
    assert monitor["open_orders"] >= 0
