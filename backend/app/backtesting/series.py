"""Pure series helpers for backtest results (downsampling, monthly returns)."""

from __future__ import annotations

from decimal import Decimal

from app.backtesting.types import BacktestEquityPoint

HUNDRED = Decimal("100")


def downsample_points(
    points: list[BacktestEquityPoint], max_points: int
) -> list[BacktestEquityPoint]:
    if max_points <= 0 or len(points) <= max_points:
        return list(points)
    stride = (len(points) + max_points - 1) // max_points
    sampled = points[::stride]
    if sampled[-1] is not points[-1]:
        sampled = [*sampled, points[-1]]
    return sampled


def monthly_returns(
    points: list[BacktestEquityPoint], initial_capital: Decimal
) -> list[dict]:
    if not points:
        return []
    months: dict[str, Decimal] = {}
    order: list[str] = []
    for point in points:
        key = f"{point.timestamp.year:04d}-{point.timestamp.month:02d}"
        if key not in months:
            order.append(key)
        months[key] = point.equity

    results: list[dict] = []
    previous = initial_capital
    for key in order:
        equity = months[key]
        change = (equity - previous) / previous * HUNDRED if previous else Decimal("0")
        results.append({"month": key, "return_pct": str(change.quantize(Decimal("0.0001")))})
        previous = equity
    return results


def drawdown_curve(points: list[BacktestEquityPoint]) -> list[tuple]:
    return [(point.timestamp, point.drawdown_pct) for point in points]
