"""Strategy registry tests."""

from __future__ import annotations

import pytest
from app.strategies import registry
from app.strategies.enums import StrategyKey
from app.strategies.registry import build, get_class, keys
from app.strategies.trend_following import TrendFollowingStrategy


def test_expected_strategies_registered() -> None:
    assert set(keys()) == {"trend_following", "momentum", "mean_reversion"}


def test_build_returns_instance() -> None:
    strategy = build(StrategyKey.TREND_FOLLOWING)
    assert isinstance(strategy, TrendFollowingStrategy)
    assert strategy.key is StrategyKey.TREND_FOLLOWING
    assert get_class("momentum").__name__ == "MomentumStrategy"


def test_unknown_key_raises() -> None:
    with pytest.raises(KeyError):
        get_class("does_not_exist")


def test_duplicate_registration_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(registry._REGISTRY, "trend_following", object())  # noqa: SLF001
    with pytest.raises(ValueError):
        registry.register(TrendFollowingStrategy)
