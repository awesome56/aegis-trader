"""Health check endpoints (liveness/readiness + component status)."""

from __future__ import annotations

import asyncio
import time
from datetime import UTC, datetime

from fastapi import APIRouter, Response, status

from app import __version__
from app.core.config import get_settings
from app.database.redis import check_redis
from app.database.session import check_database
from app.schemas.health import ComponentHealth, HealthResponse

router = APIRouter(tags=["health"])


async def _timed(coro) -> tuple[bool, float]:  # type: ignore[no-untyped-def]
    start = time.perf_counter()
    healthy = await coro
    return healthy, (time.perf_counter() - start) * 1000


@router.get("/health", response_model=HealthResponse, summary="Aggregate health")
async def health() -> HealthResponse:
    settings = get_settings()
    (db_ok, db_ms), (redis_ok, redis_ms) = await asyncio.gather(
        _timed(check_database()),
        _timed(check_redis()),
    )
    components = [
        ComponentHealth(
            name="database",
            status="healthy" if db_ok else "unhealthy",
            latency_ms=round(db_ms, 2),
        ),
        ComponentHealth(
            name="redis",
            status="healthy" if redis_ok else "unhealthy",
            latency_ms=round(redis_ms, 2),
        ),
    ]
    all_ok = db_ok and redis_ok
    return HealthResponse(
        status="healthy" if all_ok else "degraded",
        service=settings.APP_NAME,
        version=__version__,
        environment=settings.ENVIRONMENT,
        timestamp=datetime.now(UTC),
        components=components,
    )


@router.get("/health/live", summary="Liveness probe")
async def liveness() -> dict[str, str]:
    return {"status": "alive"}


@router.get("/health/ready", summary="Readiness probe")
async def readiness(response: Response) -> dict[str, str]:
    if not await check_database():
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "not_ready", "reason": "database"}
    return {"status": "ready"}
