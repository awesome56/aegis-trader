"""Exposure and concentration rules (position, portfolio, sector, asset class)."""

from __future__ import annotations

from decimal import Decimal

from app.models.enums import TradeSide
from app.risk.base import RiskRule
from app.risk.enums import RuleSeverity
from app.risk.sizing import requested_quantity, resolve_entry_price
from app.risk.types import RiskContext, RuleResult


def _reducible_result(
    rule: RiskRule,
    *,
    requested: Decimal,
    cap: Decimal | None,
    current: Decimal | None,
    limit: Decimal | None,
    label: str,
) -> RuleResult:
    if cap is None:
        return rule._result(  # noqa: SLF001
            passed=True, message=f"{label} not constrained", severity=RuleSeverity.INFO
        )
    if requested <= cap:
        return rule._result(  # noqa: SLF001
            passed=True,
            message=f"{label} within limit",
            severity=RuleSeverity.INFO,
            current=current,
            limit=limit,
        )
    severity = RuleSeverity.BLOCKING if cap <= 0 else RuleSeverity.WARNING
    message = (
        f"{label} limit reached" if cap <= 0 else f"{label} exceeds limit; size reduced to {cap}"
    )
    return rule._result(  # noqa: SLF001
        passed=False, message=message, severity=severity, current=current, limit=limit
    )


class PositionLimitRule(RiskRule):
    key = "max_position_percent"
    order = 70

    def evaluate(self, context: RiskContext) -> RuleResult:
        if context.request.side is TradeSide.SELL:
            return self._result(
                passed=True, message="sell reduces position", severity=RuleSeverity.INFO
            )
        entry = resolve_entry_price(context.request, context.quote)
        requested = requested_quantity(context.request, entry) if entry else Decimal("0")
        return _reducible_result(
            self,
            requested=requested,
            cap=context.size_caps.get("max_position"),
            current=context.symbol_exposure_percent,
            limit=context.limits.max_position_percent,
            label="position size",
        )


class PortfolioExposureRule(RiskRule):
    key = "max_portfolio_exposure"
    order = 80

    def evaluate(self, context: RiskContext) -> RuleResult:
        if context.request.side is TradeSide.SELL:
            return self._result(
                passed=True, message="sell reduces exposure", severity=RuleSeverity.INFO
            )
        entry = resolve_entry_price(context.request, context.quote)
        requested = requested_quantity(context.request, entry) if entry else Decimal("0")
        return _reducible_result(
            self,
            requested=requested,
            cap=context.size_caps.get("max_portfolio_exposure"),
            current=context.portfolio_exposure_percent,
            limit=context.limits.max_portfolio_exposure_percent,
            label="portfolio exposure",
        )


class OpenPositionsRule(RiskRule):
    key = "max_open_positions"
    order = 90

    def evaluate(self, context: RiskContext) -> RuleResult:
        if context.has_existing_position:
            return self._result(
                passed=True,
                message="position already open for this symbol",
                severity=RuleSeverity.INFO,
                current=Decimal(context.open_positions),
                limit=Decimal(context.limits.max_open_positions),
            )
        if context.open_positions >= context.limits.max_open_positions:
            return self._result(
                passed=False,
                message="maximum number of open positions reached",
                current=Decimal(context.open_positions),
                limit=Decimal(context.limits.max_open_positions),
            )
        return self._result(
            passed=True,
            message="open position count within limit",
            severity=RuleSeverity.INFO,
            current=Decimal(context.open_positions),
            limit=Decimal(context.limits.max_open_positions),
        )


class SectorExposureRule(RiskRule):
    key = "max_sector_exposure"
    order = 100

    def evaluate(self, context: RiskContext) -> RuleResult:
        if context.request.side is TradeSide.SELL:
            return self._result(
                passed=True, message="sell reduces exposure", severity=RuleSeverity.INFO
            )
        if context.sector is None:
            policy = context.limits.unknown_sector_policy
            if policy == "reject":
                return self._result(passed=False, message="asset sector metadata is unknown")
            if policy == "warn":
                return self._result(
                    passed=True,
                    message="asset sector metadata is unknown (allowed with warning)",
                    severity=RuleSeverity.WARNING,
                )
            return self._result(
                passed=True, message="asset sector unknown (allowed)", severity=RuleSeverity.INFO
            )
        entry = resolve_entry_price(context.request, context.quote)
        requested = requested_quantity(context.request, entry) if entry else Decimal("0")
        sector_pct = (
            context.sector_exposure_value / context.equity * Decimal("100")
            if context.equity
            else Decimal("0")
        )
        return _reducible_result(
            self,
            requested=requested,
            cap=context.size_caps.get("max_sector_exposure"),
            current=sector_pct,
            limit=context.limits.max_sector_exposure_percent,
            label=f"sector ({context.sector}) exposure",
        )


class AssetClassExposureRule(RiskRule):
    key = "max_asset_class_exposure"
    order = 110

    def evaluate(self, context: RiskContext) -> RuleResult:
        if context.request.side is TradeSide.SELL:
            return self._result(
                passed=True, message="sell reduces exposure", severity=RuleSeverity.INFO
            )
        if context.asset_class is None:
            policy = context.limits.unknown_sector_policy
            if policy == "reject":
                return self._result(passed=False, message="asset class metadata is unknown")
            return self._result(
                passed=True,
                message="asset class unknown (allowed with warning)",
                severity=RuleSeverity.WARNING if policy == "warn" else RuleSeverity.INFO,
            )
        entry = resolve_entry_price(context.request, context.quote)
        requested = requested_quantity(context.request, entry) if entry else Decimal("0")
        class_pct = (
            context.asset_class_exposure_value / context.equity * Decimal("100")
            if context.equity
            else Decimal("0")
        )
        return _reducible_result(
            self,
            requested=requested,
            cap=context.size_caps.get("max_asset_class_exposure"),
            current=class_pct,
            limit=context.limits.max_asset_class_exposure_percent,
            label=f"asset class ({context.asset_class}) exposure",
        )
