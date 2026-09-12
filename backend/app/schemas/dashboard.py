"""Dashboard API schema.

Only data that genuinely exists is populated. Agent/Risk/Strategy sections are
explicitly reported as unavailable rather than faked.
"""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel

from app.portfolio.types import PortfolioSummary
from app.schemas.broker import BrokerOrderSchema
from app.schemas.notifications import NotificationSchema
from app.schemas.risk import RiskUtilizationSchema
from app.schemas.strategy import SignalSchema


class DashboardAvailability(BaseModel):
    agent: bool = False
    risk: bool = True
    strategies: bool = True
    backtesting: bool = False


class DashboardSchema(BaseModel):
    portfolio: PortfolioSummary
    trading_mode: str
    trading_state: str
    broker_provider: str
    broker_status: str
    market_data_provider: str
    market_data_status: str
    market_is_open: bool
    market_session: str
    risk_status: str
    risk_utilizations: list[RiskUtilizationSchema]
    recent_signals: list[SignalSchema]
    realtime_connections: int
    unread_notifications: int
    drawdown_percent: Decimal
    recent_orders: list[BrokerOrderSchema]
    recent_notifications: list[NotificationSchema]
    availability: DashboardAvailability
