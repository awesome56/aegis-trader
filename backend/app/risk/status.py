"""Risk status / utilization helpers."""

from __future__ import annotations

from decimal import Decimal

from app.risk.enums import RiskStatus
from app.risk.types import RiskLimitsSnapshot, RuleResult

HUNDRED = Decimal("100")
_CENT = Decimal("0.0001")


def utilization_status(
    utilization_percent: Decimal, warning: Decimal, critical: Decimal
) -> RiskStatus:
    if utilization_percent >= critical:
        return RiskStatus.CRITICAL
    if utilization_percent >= warning:
        return RiskStatus.WARNING
    return RiskStatus.SAFE


def status_from_results(results: list[RuleResult]) -> RiskStatus:
    failed = [result for result in results if not result.passed]
    if any(result.severity.value == "BLOCKING" for result in failed):
        return RiskStatus.CRITICAL
    if failed:
        return RiskStatus.WARNING
    return RiskStatus.SAFE


def overall_status(items: list[tuple[Decimal, Decimal, Decimal, Decimal]]) -> RiskStatus:
    """items: (current, limit, warning, critical) tuples."""
    worst = RiskStatus.SAFE
    for current, limit, warning, critical in items:
        ratio = utilization(current, limit)
        status = utilization_status(ratio, warning, critical)
        if status is RiskStatus.CRITICAL:
            return RiskStatus.CRITICAL
        if status is RiskStatus.WARNING:
            worst = RiskStatus.WARNING
    return worst


def utilization(current: Decimal, limit: Decimal) -> Decimal:
    if limit <= 0:
        return Decimal("100") if current > 0 else Decimal("0")
    return (current / limit * HUNDRED).quantize(_CENT)


def utilization_rows(
    *,
    limits: RiskLimitsSnapshot,
    equity: Decimal,
    exposure_percent: Decimal,
    open_positions: int,
    trades_today: int,
    drawdown_percent: Decimal,
    daily_pnl: Decimal | None,
    symbol_exposure_percent: Decimal = Decimal("0"),
    sector_exposure_percent: Decimal | None = None,
    asset_class_exposure_percent: Decimal | None = None,
    warning: Decimal = Decimal("80"),
    critical: Decimal = Decimal("100"),
) -> list[dict]:
    entries: list[tuple[str, Decimal, Decimal, str]] = [
        ("portfolio_exposure", exposure_percent, limits.max_portfolio_exposure_percent, "percent"),
        ("max_position", symbol_exposure_percent, limits.max_position_percent, "percent"),
        ("open_positions", Decimal(open_positions), Decimal(limits.max_open_positions), "count"),
        ("trades_today", Decimal(trades_today), Decimal(limits.max_trades_per_day), "count"),
        ("drawdown", abs(drawdown_percent), limits.max_drawdown_percent, "percent"),
    ]
    if sector_exposure_percent is not None:
        entries.append(
            (
                "sector_exposure",
                sector_exposure_percent,
                limits.max_sector_exposure_percent,
                "percent",
            )
        )
    if asset_class_exposure_percent is not None:
        entries.append(
            (
                "asset_class_exposure",
                asset_class_exposure_percent,
                limits.max_asset_class_exposure_percent,
                "percent",
            )
        )
    if daily_pnl is not None and equity:
        loss_pct = abs(min(Decimal("0"), daily_pnl)) / equity * HUNDRED
        entries.append(("daily_loss", loss_pct, limits.max_daily_loss_percent, "percent"))

    rows: list[dict] = []
    for key, current, limit, unit in entries:
        ratio = utilization(current, limit)
        rows.append(
            {
                "key": key,
                "current": current.quantize(_CENT),
                "limit": limit,
                "utilization_percent": ratio,
                "status": utilization_status(ratio, warning, critical),
                "unit": unit,
            }
        )
    return rows


def status_from_utilization_rows(rows: list[dict]) -> RiskStatus:
    if any(row["status"] is RiskStatus.CRITICAL for row in rows):
        return RiskStatus.CRITICAL
    if any(row["status"] is RiskStatus.WARNING for row in rows):
        return RiskStatus.WARNING
    return RiskStatus.SAFE
