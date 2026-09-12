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
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    EXECUTED = "EXECUTED"
    CANCELLED = "CANCELLED"


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


class NotificationSeverity(StrEnum):
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


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
