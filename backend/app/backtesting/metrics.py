"""Deterministic performance metrics for backtests.

Definitions (documented, no hidden assumptions):

- Returns: simple period returns from the equity curve.
- Sharpe: ``mean(returns) / pstdev(returns) * sqrt(periods_per_year)`` with a
  zero risk-free rate.
- Sortino: ``mean(returns) / downside_deviation * sqrt(periods_per_year)`` where
  downside deviation is ``sqrt(mean(min(r, 0)^2))``.
- Win rate: winning closed trades / total closed trades, in percent units.
- Profit factor: ``gross_profit / abs(gross_loss)``; ``None`` when there are no
  losing trades.
- Expectancy: ``win_rate * average_win + loss_rate * average_loss`` in account
  currency.
"""

from __future__ import annotations

import statistics
from decimal import Decimal

from app.backtesting.types import (
    BacktestEquityPoint,
    BacktestMetrics,
    BacktestTradeResult,
)

HUNDRED = Decimal("100")


def _q(value: Decimal | float, places: str = "0.0001") -> Decimal:
    if not isinstance(value, Decimal):
        value = Decimal(str(value))
    return value.quantize(Decimal(places))


def compute_metrics(
    *,
    initial_capital: Decimal,
    equity_curve: list[BacktestEquityPoint],
    trades: list[BacktestTradeResult],
    periods_per_year: float,
    exposure_pct: Decimal,
    benchmark_return_pct: Decimal | None,
) -> BacktestMetrics:
    final_capital = equity_curve[-1].equity if equity_curve else initial_capital
    total_return_pct = (
        (final_capital - initial_capital) / initial_capital * HUNDRED
        if initial_capital
        else Decimal("0")
    )

    wins = [trade for trade in trades if trade.net_pnl > 0]
    losses = [trade for trade in trades if trade.net_pnl < 0]
    num_trades = len(trades)
    win_count = len(wins)
    loss_count = len(losses)

    win_rate = (
        Decimal(win_count) / Decimal(num_trades) * HUNDRED if num_trades else Decimal("0")
    )
    average_win = (
        sum((trade.net_pnl for trade in wins), Decimal("0")) / win_count
        if win_count
        else Decimal("0")
    )
    average_loss = (
        sum((trade.net_pnl for trade in losses), Decimal("0")) / loss_count
        if loss_count
        else Decimal("0")
    )
    largest_win = max((trade.net_pnl for trade in wins), default=Decimal("0"))
    largest_loss = min((trade.net_pnl for trade in losses), default=Decimal("0"))

    gross_profit = sum((trade.net_pnl for trade in wins), Decimal("0"))
    gross_loss = sum((trade.net_pnl for trade in losses), Decimal("0"))
    profit_factor = _q(gross_profit / abs(gross_loss)) if gross_loss != 0 else None

    loss_rate = Decimal(loss_count) / Decimal(num_trades) if num_trades else Decimal("0")
    expectancy = win_rate / HUNDRED * average_win + loss_rate * average_loss

    max_drawdown, max_drawdown_pct = _drawdown(equity_curve)

    returns: list[float] = []
    for previous, current in zip(equity_curve, equity_curve[1:], strict=False):
        if previous.equity > 0:
            returns.append(float((current.equity - previous.equity) / previous.equity))
    sharpe = _ratio(returns, periods_per_year, downside=False)
    sortino = _ratio(returns, periods_per_year, downside=True)

    total_fees = sum((trade.fees for trade in trades), Decimal("0"))
    total_slippage = sum((trade.slippage for trade in trades), Decimal("0"))
    average_holding = (
        sum((Decimal(trade.holding_period_seconds) for trade in trades), Decimal("0")) / num_trades
        if num_trades
        else Decimal("0")
    )

    return BacktestMetrics(
        initial_capital=_q(initial_capital),
        final_capital=_q(final_capital),
        net_profit=_q(final_capital - initial_capital),
        total_return_pct=_q(total_return_pct),
        benchmark_return_pct=_q(benchmark_return_pct) if benchmark_return_pct is not None else None,
        num_trades=num_trades,
        wins=win_count,
        losses=loss_count,
        win_rate=_q(win_rate),
        average_win=_q(average_win),
        average_loss=_q(average_loss),
        largest_win=_q(largest_win),
        largest_loss=_q(largest_loss),
        gross_profit=_q(gross_profit),
        gross_loss=_q(gross_loss),
        profit_factor=profit_factor,
        expectancy=_q(expectancy),
        max_drawdown=_q(max_drawdown),
        max_drawdown_pct=_q(max_drawdown_pct),
        sharpe_ratio=_q(sharpe) if sharpe is not None else None,
        sortino_ratio=_q(sortino) if sortino is not None else None,
        total_fees=_q(total_fees),
        total_slippage=_q(total_slippage),
        average_holding_seconds=_q(average_holding),
        exposure_pct=_q(exposure_pct),
    )


def _drawdown(equity_curve: list[BacktestEquityPoint]) -> tuple[Decimal, Decimal]:
    peak = Decimal("0")
    max_dd = Decimal("0")
    max_dd_pct = Decimal("0")
    for point in equity_curve:
        peak = max(peak, point.equity)
        if peak > 0:
            drawdown = peak - point.equity
            drawdown_pct = drawdown / peak * HUNDRED
            if drawdown > max_dd:
                max_dd = drawdown
            if drawdown_pct > max_dd_pct:
                max_dd_pct = drawdown_pct
    return max_dd, max_dd_pct


def _ratio(returns: list[float], periods_per_year: float, *, downside: bool) -> float | None:
    if len(returns) < 2:
        return None
    mean = statistics.fmean(returns)
    if downside:
        deviation = (sum(min(rate, 0.0) ** 2 for rate in returns) / len(returns)) ** 0.5
    else:
        deviation = statistics.pstdev(returns)
    if deviation == 0:
        return None
    return mean / deviation * (periods_per_year ** 0.5)
