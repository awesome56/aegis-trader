"""Import all ORM models so they register with the declarative metadata.

Alembic autogenerate and relationship resolution depend on this module being
imported before metadata is inspected.
"""

from app.models.agent import AgentDecision, AgentRun
from app.models.asset import Asset, Watchlist, WatchlistItem
from app.models.backtest import Backtest, BacktestResult
from app.models.base import Base
from app.models.broker import BrokerAccount
from app.models.enums import (
    AssetClass,
    BacktestStatus,
    BrokerMode,
    MarketRegime,
    NotificationSeverity,
    OrderAction,
    OrderStatus,
    OrderType,
    PositionSide,
    ProposalStatus,
    RiskDecision,
    RiskLevel,
    RunStatus,
    SignalDirection,
    StrategyType,
    TimeHorizon,
    TradeSide,
    TradingState,
)
from app.models.market import MarketCandle, MarketQuote
from app.models.order import Execution, Order, Trade
from app.models.portfolio import Portfolio, PortfolioSnapshot
from app.models.position import Position
from app.models.proposal import RiskEvaluation, TradeProposal
from app.models.risk import RiskSnapshot
from app.models.strategy import Strategy, StrategySignal
from app.models.system import Notification, SystemEvent
from app.models.user import User, UserSession

__all__ = [
    "Asset",
    "AssetClass",
    "AgentDecision",
    "AgentRun",
    "Backtest",
    "BacktestResult",
    "BacktestStatus",
    "Base",
    "BrokerAccount",
    "BrokerMode",
    "Execution",
    "MarketCandle",
    "MarketQuote",
    "MarketRegime",
    "Notification",
    "NotificationSeverity",
    "Order",
    "OrderAction",
    "OrderStatus",
    "OrderType",
    "Portfolio",
    "PortfolioSnapshot",
    "Position",
    "PositionSide",
    "ProposalStatus",
    "RiskDecision",
    "RiskEvaluation",
    "RiskLevel",
    "RiskSnapshot",
    "RunStatus",
    "SignalDirection",
    "Strategy",
    "StrategySignal",
    "StrategyType",
    "SystemEvent",
    "TimeHorizon",
    "Trade",
    "TradeProposal",
    "TradeSide",
    "TradingState",
    "User",
    "UserSession",
    "Watchlist",
    "WatchlistItem",
]
