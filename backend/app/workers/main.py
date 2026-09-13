"""ARQ worker entrypoint.

Run locally with::

    python -m arq app.workers.main.WorkerSettings

Schedules come from the ``WORKER_*_INTERVAL_SECONDS`` settings so operators can
tune cadence without code changes. Workers are stateless; all durable state lives
in PostgreSQL and Redis only holds locks/heartbeats.
"""

from __future__ import annotations

from typing import Any

from arq import cron
from arq.connections import RedisSettings

from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.workers.heartbeat import write_heartbeat
from app.workers.jobs import (
    evaluate_strategies,
    monitor_open_orders,
    portfolio_snapshot,
    run_agent,
    run_backtest,
)

logger = get_logger(__name__)


def seconds_schedule(interval_seconds: int) -> set[int]:
    """Second-of-minute set for sub-minute intervals."""
    step = max(1, min(interval_seconds, 59))
    return set(range(0, 60, step))


def minute_schedule(interval_seconds: int) -> set[int]:
    """Minute-of-hour set for minute-or-longer intervals."""
    step = max(1, min(interval_seconds // 60, 59))
    return set(range(0, 60, step))


def _schedule(interval_seconds: int) -> dict[str, set[int]]:
    if interval_seconds < 60:
        return {"second": seconds_schedule(interval_seconds)}
    return {"minute": minute_schedule(interval_seconds)}


async def startup(ctx: dict[str, Any]) -> None:
    settings = get_settings()
    ctx["settings"] = settings
    logger.info(
        "worker_startup",
        environment=settings.ENVIRONMENT,
        portfolio_interval=settings.WORKER_PORTFOLIO_SNAPSHOT_INTERVAL_SECONDS,
        strategy_interval=settings.WORKER_STRATEGY_EVALUATION_INTERVAL_SECONDS,
        open_order_interval=settings.WORKER_OPEN_ORDER_INTERVAL_SECONDS,
    )
    if ctx.get("redis") is not None:
        await write_heartbeat(ctx["redis"], settings)


async def shutdown(ctx: dict[str, Any]) -> None:  # noqa: ARG001
    logger.info("worker_shutdown")


def build_cron_jobs(settings: Settings | None = None) -> list[Any]:
    settings = settings or get_settings()
    return [
        cron(
            portfolio_snapshot,
            **_schedule(settings.WORKER_PORTFOLIO_SNAPSHOT_INTERVAL_SECONDS),
            run_at_startup=True,
        ),
        cron(
            evaluate_strategies,
            **_schedule(settings.WORKER_STRATEGY_EVALUATION_INTERVAL_SECONDS),
            run_at_startup=False,
        ),
        cron(
            monitor_open_orders,
            **_schedule(settings.WORKER_OPEN_ORDER_INTERVAL_SECONDS),
            run_at_startup=False,
        ),
    ]


class WorkerSettings:
    functions = [
        portfolio_snapshot,
        evaluate_strategies,
        monitor_open_orders,
        run_backtest,
        run_agent,
    ]
    cron_jobs = build_cron_jobs()
    redis_settings = RedisSettings.from_dsn(get_settings().REDIS_URL)
    on_startup = startup
    on_shutdown = shutdown
    max_jobs = 4
    job_timeout = 300
    keep_result = 300
