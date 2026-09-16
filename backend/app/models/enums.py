"""Domain enumerations shared across models, schemas, and services."""

from __future__ import annotations

from enum import StrEnum


class AssetClass(StrEnum):
    EQUITY = "EQUITY"
    ETF = "ETF"
    CRYPTO = "CRYPTO"
    FOREX = "FOREX"
    FUTURE = "FUTURE"
    OPTION = "OPTION"
    COMMODITY = "COMMODITY"


class OrderAction(StrEnum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"
    CLOSE = "CLOSE"
    REDUCE = "REDUCE"


class OrderType(StrEnum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"
    STOP_LIMIT = "STOP_LIMIT"


class OrderStatus(StrEnum):
    CREATED = "CREATED"
    VALIDATED = "VALIDATED"
    SUBMITTED = "SUBMITTED"
    ACCEPTED = "ACCEPTED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    FAILED = "FAILED"

    @property
    def is_terminal(self) -> bool:
        return self in {
            OrderStatus.FILLED,
            OrderStatus.CANCELLED,
            OrderStatus.REJECTED,
            OrderStatus.FAILED,
        }


class ProposalStatus(StrEnum):
    DRAFT = "DRAFT"
    PENDING = "PENDING"
    PENDING_RISK = "PENDING_RISK"
    RISK_APPROVED = "RISK_APPROVED"
    RISK_REJECTED = "RISK_REJECTED"
    READY_FOR_EXECUTION = "READY_FOR_EXECUTION"
    EXECUTING = "EXECUTING"
    EXECUTED = "EXECUTED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"


class ProposalSource(StrEnum):
    MANUAL = "MANUAL"
    STRATEGY = "STRATEGY"
    AGENT = "AGENT"


class PositionSide(StrEnum):
    LONG = "LONG"
    SHORT = "SHORT"


class TradeSide(StrEnum):
    BUY = "BUY"
    SELL = "SELL"


class SignalDirection(StrEnum):
    LONG = "LONG"
    SHORT = "SHORT"
    NEUTRAL = "NEUTRAL"


class StrategyType(StrEnum):
    TREND_FOLLOWING = "TREND_FOLLOWING"
    MOMENTUM = "MOMENTUM"
    MEAN_REVERSION = "MEAN_REVERSION"
    CUSTOM = "CUSTOM"


class TimeHorizon(StrEnum):
    INTRADAY = "INTRADAY"
    SWING = "SWING"
    POSITION = "POSITION"
    LONG_TERM = "LONG_TERM"


class MarketRegime(StrEnum):
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    SIDEWAYS = "SIDEWAYS"
    HIGH_VOLATILITY = "HIGH_VOLATILITY"
    LOW_VOLATILITY = "LOW_VOLATILITY"


class RiskDecision(StrEnum):
    APPROVED = "APPROVED"
    APPROVED_WITH_WARNINGS = "APPROVED_WITH_WARNINGS"
    REJECTED = "REJECTED"
    ERROR = "ERROR"


class RiskLevel(StrEnum):
    SAFE = "SAFE"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class TradingState(StrEnum):
    TRADING_ENABLED = "TRADING_ENABLED"
    TRADING_PAUSED = "TRADING_PAUSED"
    TRADING_DISABLED = "TRADING_DISABLED"
    EMERGENCY_STOP = "EMERGENCY_STOP"


class RunStatus(StrEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class BacktestStatus(StrEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class NotificationSeverity(StrEnum):
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class ProviderStatus(StrEnum):
    NOT_CONFIGURED = "NOT_CONFIGURED"
    UNTESTED = "UNTESTED"
    CONNECTED = "CONNECTED"
    ERROR = "ERROR"
    DISABLED = "DISABLED"


class AgentMode(StrEnum):
    ANALYSIS_ONLY = "ANALYSIS_ONLY"
    PROPOSE = "PROPOSE"
    AUTO_TRADE = "AUTO_TRADE"


class BrokerEnvironment(StrEnum):
    DEMO = "DEMO"
    LIVE = "LIVE"


class AutoTradeAction(StrEnum):
    OPEN = "OPEN"
    ADD = "ADD"
    HOLD = "HOLD"
    REDUCE = "REDUCE"
    CLOSE = "CLOSE"
    CANCEL_ORDER = "CANCEL_ORDER"
    REPLACE_ORDER = "REPLACE_ORDER"


class BrokerMode(StrEnum):
    PAPER = "PAPER"
    LIVE = "LIVE"


class TimeInForce(StrEnum):
    """Supported order time-in-force values.

    Only values with real semantics in the paper broker are modelled; anything
    else is rejected rather than silently accepted.
    """

    DAY = "DAY"
    GTC = "GTC"
