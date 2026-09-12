"""System status schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.models.enums import TradingState


class LiveTradingGuard(BaseModel):
    allowed: bool
    missing_requirements: list[str]


class SystemStatus(BaseModel):
    app_name: str
    version: str
    environment: str
    trading_mode: str
    live_trading_enabled: bool
    live_trading_guard: LiveTradingGuard
    broker_provider: str
    broker_status: str
    market_data_provider: str
    market_data_status: str
    realtime_connections: int
    agent_enabled: bool
    kill_switch_state: TradingState
    server_time: datetime
