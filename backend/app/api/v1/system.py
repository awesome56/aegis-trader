"""System status endpoints.

Kill-switch *actuation* and other control endpoints arrive in Phase 6; this
module exposes read-only status including the live-trading interlock.
"""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter

from app import __version__
from app.core.config import get_settings
from app.market.providers.factory import get_market_data_provider
from app.models.enums import TradingState
from app.schemas.system import LiveTradingGuard, SystemStatus

router = APIRouter(prefix="/system", tags=["system"])


async def _market_data_status() -> str:
    settings = get_settings()
    try:
        report = await get_market_data_provider(settings).health_check()
    except Exception:  # noqa: BLE001 - status must never raise
        return "UNKNOWN"
    return report.status.value


@router.get("/status", response_model=SystemStatus, summary="System and trading status")
async def status() -> SystemStatus:
    settings = get_settings()
    allowed, missing = settings.live_trading_allowed()
    return SystemStatus(
        app_name=settings.APP_NAME,
        version=__version__,
        environment=settings.ENVIRONMENT,
        trading_mode=settings.TRADING_MODE,
        live_trading_enabled=settings.LIVE_TRADING_ENABLED,
        live_trading_guard=LiveTradingGuard(allowed=allowed, missing_requirements=missing),
        broker_provider=settings.BROKER_PROVIDER,
        market_data_provider=settings.MARKET_DATA_PROVIDER,
        market_data_status=await _market_data_status(),
        agent_enabled=settings.AGENT_ENABLED,
        kill_switch_state=TradingState(settings.KILL_SWITCH_STATE),
        server_time=datetime.now(UTC),
    )
