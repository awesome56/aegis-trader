"""Agent-layer enumerations."""

from __future__ import annotations

from enum import StrEnum

from app.models.enums import AgentMode as AgentRunMode  # single source of truth

__all__ = ["AgentAction", "AgentRunMode", "EvidenceType"]


class AgentAction(StrEnum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"
    NO_ACTION = "NO_ACTION"


class EvidenceType(StrEnum):
    STRATEGY_SIGNAL = "strategy_signal"
    MARKET_REGIME = "market_regime"
    PORTFOLIO = "portfolio"
    POSITION = "position"
    RECENT_TRADE = "recent_trade"
    RISK = "risk"
    BACKTEST = "backtest"
    OTHER = "other"
