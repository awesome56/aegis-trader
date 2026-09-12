"""Deterministic strategy engine (Phase 5).

Strategies observe market data and emit analytical ``StrategySignal``s. They
never size positions, touch cash/positions, or submit orders. Dependency
direction: ``strategies -> market`` (and shared domain/config), never brokers,
orders, risk or agents.
"""

# Importing the concrete strategies registers them with the registry.
from app.strategies import mean_reversion, momentum, trend_following  # noqa: F401
from app.strategies.base import Strategy
from app.strategies.enums import EvaluationStatus, StrategyKey
from app.strategies.regime import MarketRegimeService
from app.strategies.registry import build, get_class, keys, register
from app.strategies.types import (
    RegimeAssessment,
    StrategyContext,
    StrategyEvaluationResult,
    StrategySignalResult,
)

__all__ = [
    "EvaluationStatus",
    "MarketRegimeService",
    "RegimeAssessment",
    "Strategy",
    "StrategyContext",
    "StrategyEvaluationResult",
    "StrategyKey",
    "StrategySignalResult",
    "build",
    "get_class",
    "keys",
    "register",
]
