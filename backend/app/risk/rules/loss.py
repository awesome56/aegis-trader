"""Loss, drawdown and trade-frequency rules."""

from __future__ import annotations

from decimal import Decimal

from app.risk.base import RiskRule
from app.risk.enums import RuleSeverity
from app.risk.types import RiskContext, RuleResult

HUNDRED = Decimal("100")


class DailyLossRule(RiskRule):
    key = "max_daily_loss"
    order = 120

    def evaluate(self, context: RiskContext) -> RuleResult:
        if context.daily_pnl is None:
            return self._result(
                passed=True,
                message="daily P&L unavailable (no snapshot history yet)",
                severity=RuleSeverity.WARNING,
            )
        limit_amount = context.equity * context.limits.max_daily_loss_percent / HUNDRED
        loss = abs(min(Decimal("0"), context.daily_pnl))
        if loss >= limit_amount:
            return self._result(
                passed=False,
                message="maximum daily loss limit reached",
                current=loss,
                limit=limit_amount,
            )
        return self._result(
            passed=True,
            message="within daily loss limit",
            severity=RuleSeverity.INFO,
            current=loss,
            limit=limit_amount,
        )


class DrawdownRule(RiskRule):
    key = "max_drawdown"
    order = 130

    def evaluate(self, context: RiskContext) -> RuleResult:
        drawdown = abs(context.drawdown_percent)
        if drawdown >= context.limits.max_drawdown_percent:
            return self._result(
                passed=False,
                message="maximum drawdown exceeded",
                current=drawdown,
                limit=context.limits.max_drawdown_percent,
            )
        return self._result(
            passed=True,
            message="drawdown within limit",
            severity=RuleSeverity.INFO,
            current=drawdown,
            limit=context.limits.max_drawdown_percent,
        )


class TradeFrequencyRule(RiskRule):
    key = "max_trades_per_day"
    order = 140

    def evaluate(self, context: RiskContext) -> RuleResult:
        if context.trades_today >= context.limits.max_trades_per_day:
            return self._result(
                passed=False,
                message="maximum number of trades per day reached",
                current=Decimal(context.trades_today),
                limit=Decimal(context.limits.max_trades_per_day),
            )
        return self._result(
            passed=True,
            message="trade frequency within limit",
            severity=RuleSeverity.INFO,
            current=Decimal(context.trades_today),
            limit=Decimal(context.limits.max_trades_per_day),
        )
