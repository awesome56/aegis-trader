"""Deterministic market scenarios and signal activation."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from app.core.config import Settings, get_settings
from app.market.enums import Timeframe
from app.market.providers.mock import MockMarketDataProvider
from app.repositories.order import OrderRepository
from app.repositories.proposal import TradeProposalRepository
from app.repositories.strategy import StrategySignalRepository
from app.strategies.enums import EvaluationStatus, StrategyKey
from app.strategies.regime import MarketRegimeService
from app.strategies.registry import build
from app.strategies.types import StrategyContext
from scripts.seed_strategy_signals import seed

SYMBOL = "AAPL"
TIMEFRAME = Timeframe.ONE_HOUR


def scenario_settings(scenario: str) -> Settings:
    return get_settings().model_copy(
        update={
            "MOCK_MARKET_SCENARIO": scenario,
            "MARKET_CANDLE_CACHE_TTL_SECONDS": 0,
            "MARKET_QUOTE_CACHE_TTL_SECONDS": 0,
            "STRATEGY_ANALYSIS_MAX_AGE_MULTIPLIER": 1_000_000.0,
        }
    )


async def evaluate_scenario(scenario: str):
    settings = scenario_settings(scenario)
    provider = MockMarketDataProvider(settings)
    implementations = {key.value: build(key.value, settings) for key in StrategyKey}
    required = max(impl.min_candles for impl in implementations.values())
    limit = min(max(required + 5, 60), settings.MARKET_MAX_CANDLE_LIMIT, 500)
    candles = await provider.get_latest_candles(SYMBOL, TIMEFRAME, limit)
    regime = MarketRegimeService(settings).classify(candles)
    quote = await provider.get_quote(SYMBOL)
    context = StrategyContext(
        symbol=SYMBOL,
        timeframe=TIMEFRAME,
        candles=candles,
        quote=quote,
        regime=regime,
        evaluation_time=datetime.now(UTC),
        data_timestamp=regime.data_timestamp,
    )
    return {key: impl.evaluate(context) for key, impl in implementations.items()}, regime


@pytest.mark.parametrize(
    ("scenario", "strategy", "direction"),
    [
        ("uptrend", StrategyKey.TREND_FOLLOWING.value, "LONG"),
        ("downtrend", StrategyKey.TREND_FOLLOWING.value, "SHORT"),
        ("momentum_bullish", StrategyKey.MOMENTUM.value, "LONG"),
        ("momentum_bearish", StrategyKey.MOMENTUM.value, "SHORT"),
        ("mean_reversion_oversold", StrategyKey.MEAN_REVERSION.value, "LONG"),
        ("mean_reversion_overbought", StrategyKey.MEAN_REVERSION.value, "SHORT"),
    ],
)
async def test_scenario_produces_expected_signal(scenario, strategy, direction) -> None:
    results, _ = await evaluate_scenario(scenario)
    outcome = results[strategy]
    assert outcome.status is EvaluationStatus.SIGNAL, outcome.reason
    assert outcome.signal is not None
    assert outcome.signal.direction.value == direction


async def test_sideways_suppresses_trend_signal() -> None:
    results, regime = await evaluate_scenario("sideways")
    assert regime.trend.value == "SIDEWAYS"
    assert results[StrategyKey.TREND_FOLLOWING.value].status is EvaluationStatus.NO_SIGNAL


async def test_high_volatility_regime_suppresses_strategies() -> None:
    results, regime = await evaluate_scenario("high_volatility")
    assert regime.volatility.value == "HIGH"
    for outcome in results.values():
        assert outcome.status is not EvaluationStatus.SIGNAL


async def test_scenarios_are_deterministic() -> None:
    first, _ = await evaluate_scenario("uptrend")
    second, _ = await evaluate_scenario("uptrend")
    assert (
        first[StrategyKey.TREND_FOLLOWING.value].signal.confidence
        == second[StrategyKey.TREND_FOLLOWING.value].signal.confidence
    )


async def test_seed_persists_signals_and_dedupes(db_session) -> None:
    settings = scenario_settings("uptrend")
    results = await seed(db_session, settings, symbols=[SYMBOL], timeframe="1h", enable=True)
    assert any(outcome.signal is not None for outcome in results[SYMBOL])

    signals = StrategySignalRepository(db_session)
    first = await signals.count_signals()
    assert first >= 1

    # Re-running in the same candle window must not create duplicates.
    await seed(db_session, settings, symbols=[SYMBOL], timeframe="1h", enable=True)
    assert await signals.count_signals() == first


async def test_market_overview_includes_signals_without_lazy_load(db_session) -> None:
    """Regression: persisted signals must not trigger a strategy lazy-load."""
    settings = scenario_settings("uptrend")
    await seed(db_session, settings, symbols=[SYMBOL], timeframe="1h", enable=True)

    from app.api.v1.markets import market_overview
    from app.market.services.market_data import MarketDataService

    service = MarketDataService(
        db_session, provider=MockMarketDataProvider(settings), settings=settings
    )
    overview = await market_overview(service, db_session)
    row = next(item for item in overview.items if item.symbol == SYMBOL)
    assert row.signal_direction == "LONG"
    assert row.strategy == "trend_following"


async def test_seed_creates_no_proposals_or_orders(db_session) -> None:
    settings = scenario_settings("mean_reversion_oversold")
    await seed(db_session, settings, symbols=[SYMBOL], timeframe="1h", enable=True)

    _, portfolio = await _portfolio(db_session)
    assert await TradeProposalRepository(db_session).count_for_portfolio(portfolio.id) == 0
    assert await OrderRepository(db_session).count_for_account(portfolio.broker_account_id) == 0


async def _portfolio(session):
    from app.brokers.bootstrap import ensure_paper_account
    from app.models.user import User
    from sqlalchemy import select

    user = (
        await session.execute(select(User).where(User.email == "seed-signals@example.com"))
    ).scalar_one_or_none()
    if user is None:
        user = User(email="seed-signals@example.com", hashed_password="x", is_active=True)
        session.add(user)
        await session.flush()
    return await ensure_paper_account(session, user)
