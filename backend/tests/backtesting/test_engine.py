"""Backtesting engine + metrics unit tests (no DB, no provider)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from app.backtesting.engine import BacktestingEngine
from app.backtesting.exceptions import (
    BacktestDataError,
    BacktestInsufficientData,
    BacktestValidationError,
)
from app.backtesting.metrics import compute_metrics
from app.backtesting.types import BacktestConfig, BacktestExitReason
from app.core.config import get_settings
from app.market.domain.models import Candle
from app.market.enums import Timeframe
from app.market.providers import scenarios

START = datetime(2026, 1, 1, tzinfo=UTC)
TF = Timeframe.ONE_HOUR


def build_candles(scenario: str, count: int, *, base: float = 100.0, mutate=None) -> list[Candle]:
    closes = scenarios.scenario_closes(scenario, count, base)
    env = scenarios.envelope(scenario)
    volumes = scenarios.scenario_volumes(scenario, count)
    candles: list[Candle] = []
    for index, close in enumerate(closes):
        if mutate is not None:
            close = mutate(index, close)
        open_time = START + timedelta(hours=index)
        open_price = closes[index - 1] if index > 0 else close * (1 - env)
        if mutate is not None and index > 0:
            open_price = mutate(index - 1, closes[index - 1])
        candles.append(
            Candle(
                symbol="AAPL",
                timeframe=TF,
                open_time=open_time,
                close_time=open_time + timedelta(hours=1),
                open=Decimal(str(open_price)),
                high=Decimal(str(max(open_price, close) * (1 + env))),
                low=Decimal(str(min(open_price, close) * (1 - env))),
                close=Decimal(str(close)),
                volume=volumes[index],
                provider="scenario",
            )
        )
    return candles


def config(**overrides) -> BacktestConfig:
    base = dict(
        strategy_key="trend_following",
        symbols=["AAPL"],
        timeframe="1h",
        start=START,
        end=START + timedelta(hours=200),
        initial_capital=Decimal("100000"),
        position_size_percent=Decimal("100"),
        fees_pct=Decimal("0"),
        slippage_pct=Decimal("0"),
    )
    base.update(overrides)
    return BacktestConfig(**base)


def engine() -> BacktestingEngine:
    return BacktestingEngine(get_settings())


def test_uptrend_produces_trades_and_positive_return() -> None:
    result = engine().run(config(), build_candles("uptrend", 90))
    assert result.metrics.num_trades >= 1
    assert result.metrics.final_capital > result.metrics.initial_capital
    assert result.trades[-1].exit_reason is BacktestExitReason.END_OF_BACKTEST
    assert len(result.equity_curve) == 90


def test_insufficient_data_raises() -> None:
    with pytest.raises(BacktestInsufficientData):
        engine().run(config(), build_candles("uptrend", 40))


def test_empty_data_raises() -> None:
    with pytest.raises(BacktestDataError):
        engine().run(config(), [])


def test_multi_symbol_rejected_in_v1() -> None:
    with pytest.raises(BacktestValidationError):
        engine().run(config(symbols=["AAPL", "MSFT"]), build_candles("uptrend", 90))


def test_commission_and_slippage_reduce_final_capital() -> None:
    candles = build_candles("uptrend", 90)
    free = engine().run(config(), candles)
    costly = engine().run(
        config(fees_pct=Decimal("0.1"), slippage_pct=Decimal("0.1")), candles
    )
    assert costly.metrics.final_capital < free.metrics.final_capital
    assert costly.metrics.total_fees > 0
    assert costly.metrics.total_slippage > 0


def test_no_lookahead_future_candles_do_not_change_past_decisions() -> None:
    divergence = 70
    baseline = build_candles("uptrend", 90)

    def mutate(index: int, close: float) -> float:
        return close * 3 if index >= divergence else close

    altered = build_candles("uptrend", 90, mutate=mutate)
    cutoff = baseline[divergence].open_time

    base_result = engine().run(config(), baseline)
    alt_result = engine().run(config(), altered)

    def before(cutoff_time, trades):
        return [t.model_dump(mode="json") for t in trades if t.exit_time < cutoff_time]

    assert before(cutoff, base_result.trades) == before(cutoff, alt_result.trades)


def _point(hours: int, equity: str, ret: str, drawdown: str):
    from app.backtesting.types import BacktestEquityPoint

    return BacktestEquityPoint(
        timestamp=START + timedelta(hours=hours),
        cash=Decimal(equity),
        positions_value=Decimal("0"),
        equity=Decimal(equity),
        cumulative_return_pct=Decimal(ret),
        drawdown_pct=Decimal(drawdown),
    )


def test_metrics_known_dataset() -> None:
    from app.backtesting.types import BacktestTradeResult

    equity = [
        _point(0, "110000", "10", "0"),
        _point(1, "105000", "5", "4.5455"),
        _point(2, "120000", "20", "0"),
    ]

    def trade(pnl: str, fees: str = "0", seconds: int = 3600) -> BacktestTradeResult:
        return BacktestTradeResult(
            symbol="AAPL", side="LONG", quantity=Decimal("1"),
            entry_time=START, entry_price=Decimal("100"),
            exit_time=START + timedelta(hours=1), exit_price=Decimal("100"),
            gross_pnl=Decimal(pnl), fees=Decimal(fees), slippage=Decimal("0"),
            net_pnl=Decimal(pnl), return_pct=Decimal("0"),
            holding_period_seconds=seconds, exit_reason=BacktestExitReason.SIGNAL,
        )

    metrics = compute_metrics(
        initial_capital=Decimal("100000"),
        equity_curve=equity,
        trades=[trade("200", fees="10"), trade("-100", fees="5")],
        periods_per_year=8760.0,
        exposure_pct=Decimal("50"),
        benchmark_return_pct=Decimal("8"),
    )
    assert metrics.final_capital == Decimal("120000")
    assert metrics.total_return_pct == Decimal("20.0000")
    assert metrics.wins == 1 and metrics.losses == 1
    assert metrics.win_rate == Decimal("50.0000")
    assert metrics.average_win == Decimal("200.0000")
    assert metrics.average_loss == Decimal("-100.0000")
    assert metrics.gross_profit == Decimal("200.0000")
    assert metrics.gross_loss == Decimal("-100.0000")
    assert metrics.profit_factor == Decimal("2.0000")
    assert metrics.expectancy == Decimal("50.0000")
    assert metrics.max_drawdown == Decimal("5000.0000")
    assert metrics.max_drawdown_pct == Decimal("4.5455")
    assert metrics.total_fees == Decimal("15.0000")
    assert metrics.benchmark_return_pct == Decimal("8.0000")
    assert metrics.sharpe_ratio is not None
    assert metrics.sortino_ratio is not None


def test_profit_factor_none_without_losses() -> None:
    from app.backtesting.types import BacktestTradeResult

    equity = [
        _point(0, "101000", "1", "0"),
        _point(1, "102000", "2", "0"),
    ]
    winning = BacktestTradeResult(
        symbol="AAPL", side="LONG", quantity=Decimal("1"),
        entry_time=START, entry_price=Decimal("100"),
        exit_time=START + timedelta(hours=1), exit_price=Decimal("102"),
        gross_pnl=Decimal("2"), fees=Decimal("0"), slippage=Decimal("0"),
        net_pnl=Decimal("2"), return_pct=Decimal("2"),
        holding_period_seconds=3600, exit_reason=BacktestExitReason.SIGNAL,
    )
    metrics = compute_metrics(
        initial_capital=Decimal("100000"), equity_curve=equity, trades=[winning],
        periods_per_year=8760.0, exposure_pct=Decimal("100"), benchmark_return_pct=None,
    )
    assert metrics.profit_factor is None
    assert metrics.win_rate == Decimal("100.0000")
