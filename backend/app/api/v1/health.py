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
from app.market.enums import ProviderStatus
from app.market.providers.factory import get_market_data_provider
from app.schemas.health import ComponentHealth, ComponentState, HealthResponse

router = APIRouter(tags=["health"])

_PROVIDER_STATE: dict[ProviderStatus, ComponentState] = {
    ProviderStatus.CONNECTED: "healthy",
    ProviderStatus.MOCK: "healthy",
    ProviderStatus.DEGRADED: "degraded",
    ProviderStatus.DISCONNECTED: "unhealthy",
}


async def _timed_bool(coro) -> tuple[bool, float]:  # type: ignore[no-untyped-def]
    start = time.perf_counter()
    healthy = await coro
    return healthy, (time.perf_counter() - start) * 1000


async def _market_data_health() -> ComponentHealth:
    settings = get_settings()
    start = time.perf_counter()
    try:
        provider = get_market_data_provider(settings)
        report = await provider.health_check()
    except Exception as exc:  # noqa: BLE001 - health must never raise
        return ComponentHealth(
            name="market_data",
            status="unhealthy",
            latency_ms=round((time.perf_counter() - start) * 1000, 2),
            detail=f"provider={settings.MARKET_DATA_PROVIDER} error={exc}",
        )
    return ComponentHealth(
        name="market_data",
        status=_PROVIDER_STATE[report.status],
        latency_ms=round((time.perf_counter() - start) * 1000, 2),
        detail=f"provider={report.provider} status={report.status.value}",
    )


@router.get("/health", response_model=HealthResponse, summary="Aggregate health")
async def health() -> HealthResponse:
    settings = get_settings()
    (db_ok, db_ms), (redis_ok, redis_ms) = await asyncio.gather(
        _timed_bool(check_database()),
        _timed_bool(check_redis()),
    )
    market = await _market_data_health()

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
        market,
    ]
    all_ok = db_ok and redis_ok and market.status in {"healthy", "degraded"}
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
