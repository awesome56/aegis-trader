"""Enqueue background jobs onto the existing ARQ/Redis worker.

Best-effort: returns ``False`` when Redis is unavailable so callers can fall back
to executing inline (development/tests).
"""

from __future__ import annotations

import uuid

from arq import create_pool
from arq.connections import RedisSettings

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


async def enqueue_backtest(backtest_id: uuid.UUID) -> bool:
    settings = get_settings()
    try:
        pool = await create_pool(RedisSettings.from_dsn(settings.REDIS_URL))
        try:
            await pool.enqueue_job("run_backtest", str(backtest_id))
        finally:
            await pool.aclose()
        return True
    except Exception as exc:  # noqa: BLE001 - caller falls back to inline execution
        logger.warning("backtest_enqueue_failed", error=str(exc))
        return False
