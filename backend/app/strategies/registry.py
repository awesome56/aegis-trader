"""Strategy registry: one place that maps stable keys to implementations."""

from __future__ import annotations

from app.core.config import Settings
from app.strategies.base import Strategy
from app.strategies.enums import StrategyKey

_REGISTRY: dict[str, type[Strategy]] = {}


def register(strategy_class: type[Strategy]) -> type[Strategy]:
    key = strategy_class.key.value
    if key in _REGISTRY and _REGISTRY[key] is not strategy_class:
        raise ValueError(f"Duplicate strategy key registration: {key}")
    _REGISTRY[key] = strategy_class
    return strategy_class


def keys() -> list[str]:
    return list(_REGISTRY)


def get_class(key: str | StrategyKey) -> type[Strategy]:
    normalized = key.value if isinstance(key, StrategyKey) else str(key)
    if normalized not in _REGISTRY:
        raise KeyError(f"Unknown strategy key: {normalized}")
    return _REGISTRY[normalized]


def build(key: str | StrategyKey, settings: Settings | None = None) -> Strategy:
    return get_class(key)(settings)
