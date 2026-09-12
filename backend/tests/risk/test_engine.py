"""Deterministic RiskEngine end-to-end tests (DB-backed, no side effects)."""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from app.brokers.types import BrokerOrderRequest
from app.models.enums import RiskDecision, TradeSide, TradingState
from app.models.portfolio import PortfolioSnapshot
from app.repositories.order import OrderRepository
from app.repositories.portfolio import PortfolioSnapshotRepository
from app.risk.types import RiskRequest

from tests.risk.conftest import NOW

ENTRY = Decimal("139.5")


def _buy(qty: str = "5", **overrides: object) -> RiskRequest:
    values: dict[str, object] = {
        "symbol": "AAPL",
        "side": TradeSide.BUY,
        "requested_quantity": Decimal(qty),
        "entry_price": ENTRY,
        "stop_loss": Decimal("135"),
        "take_profit": Decimal("150"),
        "source": "test",
    }
    values.update(overrides)
    return RiskRequest(**values)  # type: ignore[arg-type]


async def _snapshot(env, *, days_ago: int, equity: str) -> None:  # noqa: ANN001
    repo = PortfolioSnapshotRepository(env.session)
    value = Decimal(equity)
    await repo.add(
        PortfolioSnapshot(
            portfolio_id=env.portfolio.id,
            snapshot_time=NOW - timedelta(days=days_ago),
            cash=value,
            equity=value,
            buying_power=value,
            invested=Decimal("0"),
            market_value=Decimal("0"),
            unrealized_pnl=Decimal("0"),
            realized_pnl=Decimal("0"),
            daily_pnl=Decimal("0"),
            total_return_pct=Decimal("0"),
            daily_return_pct=Decimal("0"),
            exposure_pct=Decimal("0"),
            position_count=0,
        )
    )


async def test_approved_within_limits(risk_env) -> None:  # noqa: ANN001
    env = await risk_env()
    result = await env.engine.evaluate(_buy("5"))
    assert result.decision is RiskDecision.APPROVED
    assert result.approved_quantity == Decimal("5")
    assert result.reasons == []
    assert result.entry_price == ENTRY


async def test_oversized_reduced(risk_env) -> None:  # noqa: ANN001
    env = await risk_env()
    result = await env.engine.evaluate(_buy("1000"))
    assert result.decision is RiskDecision.APPROVED_WITH_WARNINGS
    assert result.approved_quantity is not None
    assert result.approved_quantity < Decimal("1000")
    assert "MAX_POSITION_PERCENT" in result.warnings


async def test_portfolio_exposure_cap(risk_env) -> None:  # noqa: ANN001
    env = await risk_env(MAX_PORTFOLIO_EXPOSURE=1.0, MAX_POSITION_PERCENTAGE=100.0)
    result = await env.engine.evaluate(_buy("1000"))
    assert result.decision is RiskDecision.APPROVED_WITH_WARNINGS
    assert "MAX_PORTFOLIO_EXPOSURE" in result.warnings


async def test_insufficient_buying_power_rejected(risk_env) -> None:  # noqa: ANN001
    env = await risk_env(PAPER_INITIAL_BALANCE=100.0)
    result = await env.engine.evaluate(_buy("5"))
    assert result.decision is RiskDecision.REJECTED
    assert "BUYING_POWER" in result.reasons


async def test_missing_stop_loss_rejected(risk_env) -> None:  # noqa: ANN001
    env = await risk_env()
    result = await env.engine.evaluate(_buy("5", stop_loss=None, take_profit=None))
    assert result.decision is RiskDecision.REJECTED
    assert "STOP_LOSS" in result.reasons


async def test_poor_reward_risk_rejected(risk_env) -> None:  # noqa: ANN001
    env = await risk_env()
    result = await env.engine.evaluate(
        _buy("5", stop_loss=Decimal("138.5"), take_profit=Decimal("140"))
    )
    assert result.decision is RiskDecision.REJECTED
    assert "REWARD_RISK" in result.reasons


async def test_stale_market_data_rejected(risk_env) -> None:  # noqa: ANN001
    env = await risk_env(
        data_now=NOW,
        clock_now=NOW + timedelta(days=1),
        MAX_QUOTE_AGE_SECONDS=15,
    )
    result = await env.engine.evaluate(_buy("5"))
    assert result.decision is RiskDecision.REJECTED
    assert "MARKET_FRESHNESS" in result.reasons


async def test_emergency_stop_rejected(risk_env) -> None:  # noqa: ANN001
    env = await risk_env()
    from app.risk.trading_state import TradingStateService

    service = TradingStateService(env.session, settings=env.settings, clock=lambda: env.now)
    await service.transition(TradingState.EMERGENCY_STOP, reason="test", actor="t")
    result = await env.engine.evaluate(_buy("5"))
    assert result.decision is RiskDecision.REJECTED
    assert "TRADING_STATE" in result.reasons


async def test_daily_loss_rejected(risk_env) -> None:  # noqa: ANN001
    env = await risk_env()
    await _snapshot(env, days_ago=1, equity="200000")
    result = await env.engine.evaluate(_buy("5"))
    assert result.decision is RiskDecision.REJECTED
    assert "MAX_DAILY_LOSS" in result.reasons


async def test_drawdown_rejected(risk_env) -> None:  # noqa: ANN001
    env = await risk_env(MAX_DAILY_LOSS_PERCENTAGE=100.0)
    await _snapshot(env, days_ago=3, equity="150000")
    result = await env.engine.evaluate(_buy("5"))
    assert result.decision is RiskDecision.REJECTED
    assert "MAX_DRAWDOWN" in result.reasons


async def test_trade_frequency_rejected(risk_env) -> None:  # noqa: ANN001
    env = await risk_env(MAX_TRADES_PER_DAY=1)
    await env.broker.submit_order(
        BrokerOrderRequest(
            symbol="AAPL", side=TradeSide.BUY, quantity=Decimal("1"), idempotency_key="tf"
        )
    )
    result = await env.engine.evaluate(_buy("1"))
    assert result.decision is RiskDecision.REJECTED
    assert "MAX_TRADES_PER_DAY" in result.reasons


async def test_low_confidence_rejected(risk_env) -> None:  # noqa: ANN001
    env = await risk_env()
    result = await env.engine.evaluate(_buy("5", strategy_confidence=Decimal("0.1")))
    assert result.decision is RiskDecision.REJECTED
    assert "STRATEGY_CONFIDENCE" in result.reasons


async def test_risk_engine_disabled_is_error(risk_env) -> None:  # noqa: ANN001
    env = await risk_env(RISK_ENABLED=False)
    result = await env.engine.evaluate(_buy("5"))
    assert result.decision is RiskDecision.ERROR


async def test_evaluation_persists_and_has_no_side_effects(risk_env) -> None:  # noqa: ANN001
    env = await risk_env()
    cash_before = (await env.broker.get_account()).cash
    result = await env.engine.evaluate(_buy("5"))
    assert result.id is not None

    from app.repositories.risk import RiskEvaluationRepository

    stored = await RiskEvaluationRepository(env.session).get(result.id)
    assert stored is not None
    assert stored.reasons == []
    assert stored.checks

    # No order was created and cash is unchanged.
    assert await OrderRepository(env.session).count_for_account(env.account.id) == 0
    assert (await env.broker.get_account()).cash == cash_before


async def test_rejected_evaluation_persists_reasons(risk_env) -> None:  # noqa: ANN001
    env = await risk_env()
    result = await env.engine.evaluate(_buy("5", stop_loss=None, take_profit=None))
    from app.repositories.risk import RiskEvaluationRepository

    stored = await RiskEvaluationRepository(env.session).get(result.id)
    assert stored is not None
    assert "STOP_LOSS" in (stored.reasons or [])
