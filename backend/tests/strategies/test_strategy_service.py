"""StrategyService orchestration, persistence and dedupe tests."""

from __future__ import annotations

from datetime import timedelta

from app.models.strategy import StrategySignal
from app.strategies.enums import EvaluationStatus
from sqlalchemy import func, select

from tests.strategies.conftest import strategy_settings, uptrend
from tests.strategies.helpers import FIXED_NOW


async def test_bootstrap_is_idempotent(strategy_env) -> None:  # noqa: ANN001
    env = await strategy_env(uptrend())
    slugs = {strategy.slug for strategy in await env.service.list_strategies()}
    assert slugs == {"trend_following", "momentum", "mean_reversion"}
    assert await env.service.ensure_bootstrapped() == []


async def test_evaluate_persists_and_dedupes(strategy_env) -> None:  # noqa: ANN001
    env = await strategy_env(uptrend())
    results = await env.service.evaluate("TEST", "1h")
    assert any(result.status is EvaluationStatus.SIGNAL for result in results)
    assert await env.service.count_signals() == 1

    await env.service.evaluate("TEST", "1h")
    assert await env.service.count_signals() == 1

    count = await env.session.scalar(select(func.count()).select_from(StrategySignal))
    assert count == 1


async def test_disabled_strategy_skipped(strategy_env) -> None:  # noqa: ANN001
    env = await strategy_env(uptrend())
    for strategy in await env.service.list_strategies():
        await env.service.set_enabled(strategy, False)
    assert await env.service.evaluate("TEST", "1h") == []

    trend = next(s for s in await env.service.list_strategies() if s.slug == "trend_following")
    await env.service.set_enabled(trend, True)
    results = await env.service.evaluate("TEST", "1h")
    assert len(results) == 1
    assert results[0].strategy_key == "trend_following"


async def test_insufficient_candles(strategy_env) -> None:  # noqa: ANN001
    env = await strategy_env(uptrend(10))
    results = await env.service.evaluate("TEST", "1h")
    assert results
    assert all(result.status is EvaluationStatus.INSUFFICIENT_DATA for result in results)
    assert await env.service.count_signals() == 0


async def test_stale_data_refused(strategy_env) -> None:  # noqa: ANN001
    env = await strategy_env(
        uptrend(),
        data_now=FIXED_NOW,
        clock_now=FIXED_NOW + timedelta(hours=10),
        STRATEGY_ANALYSIS_MAX_AGE_MULTIPLIER=3.0,
    )
    results = await env.service.evaluate("TEST", "1h")
    assert all(result.status is EvaluationStatus.STALE_DATA for result in results)
    assert await env.service.count_signals() == 0


async def test_signal_listing_and_filters(strategy_env) -> None:  # noqa: ANN001
    env = await strategy_env(uptrend())
    await env.service.evaluate("TEST", "1h")
    signals = await env.service.list_signals(symbol="TEST", timeframe="1h")
    assert len(signals) == 1
    assert signals[0].direction.value == "LONG"
    assert await env.service.count_signals(symbol="OTHER") == 0


async def test_evaluate_specific_strategy(strategy_env) -> None:  # noqa: ANN001
    env = await strategy_env(uptrend())
    trend = next(s for s in await env.service.list_strategies() if s.slug == "trend_following")
    results = await env.service.evaluate("TEST", "1h", strategy_ids=[trend.id])
    assert len(results) == 1
    assert results[0].strategy_key == "trend_following"


def test_settings_validation_rejects_bad_window() -> None:
    import pytest
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        strategy_settings(STRATEGY_TREND_FAST_PERIOD=60, STRATEGY_TREND_SLOW_PERIOD=50)
