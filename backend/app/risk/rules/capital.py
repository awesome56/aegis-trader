"""Capital, stop-loss, reward/risk and confidence rules."""

from __future__ import annotations

from decimal import Decimal

from app.models.enums import TradeSide
from app.risk.base import RiskRule
from app.risk.enums import RuleSeverity
from app.risk.sizing import requested_quantity, resolve_entry_price
from app.risk.types import RiskContext, RuleResult

HUNDRED = Decimal("100")


class BuyingPowerRule(RiskRule):
    key = "buying_power"
    order = 40

    def evaluate(self, context: RiskContext) -> RuleResult:
        if context.request.side is TradeSide.SELL:
            return self._result(
                passed=True, message="sell reduces exposure", severity=RuleSeverity.INFO
            )
        entry = resolve_entry_price(context.request, context.quote)
        cap = context.size_caps.get("buying_power")
        if entry is None or cap is None:
            return self._result(passed=False, message="buying power cannot be determined")
        requested = requested_quantity(context.request, entry)
        if requested <= cap:
            return self._result(
                passed=True,
                message="within buying power",
                severity=RuleSeverity.INFO,
                current=requested,
                limit=cap,
            )
        if cap <= 0:
            return self._result(
                passed=False, message="insufficient buying power", current=requested, limit=cap
            )
        return self._result(
            passed=False,
            message="requested size exceeds buying power; size reduced",
            severity=RuleSeverity.WARNING,
            current=requested,
            limit=cap,
        )


class StopLossRule(RiskRule):
    key = "stop_loss"
    order = 50

    def evaluate(self, context: RiskContext) -> RuleResult:
        request = context.request
        if request.stop_loss is None:
            if not context.limits.require_stop_loss:
                return self._result(
                    passed=True,
                    message="stop loss not required",
                    severity=RuleSeverity.INFO,
                )
            return self._result(passed=False, message="stop loss is required")
        entry = resolve_entry_price(request, context.quote)
        if entry is None:
            return self._result(passed=False, message="cannot validate stop without an entry price")
        if request.side is TradeSide.BUY and request.stop_loss >= entry:
            return self._result(passed=False, message="stop loss must be below entry")
        if request.side is TradeSide.SELL and request.stop_loss <= entry:
            return self._result(passed=False, message="stop loss must be above entry")
        return self._result(
            passed=True,
            message="stop loss valid",
            severity=RuleSeverity.INFO,
            current=request.stop_loss,
        )


class RewardRiskRule(RiskRule):
    key = "reward_risk"
    order = 60

    def evaluate(self, context: RiskContext) -> RuleResult:
        request = context.request
        if request.stop_loss is None or request.take_profit is None:
            return self._result(
                passed=True,
                message="risk/reward not evaluated (stop or target missing)",
                severity=RuleSeverity.INFO,
            )
        entry = resolve_entry_price(request, context.quote)
        if entry is None:
            return self._result(passed=False, message="cannot evaluate risk/reward without entry")
        risk = abs(entry - request.stop_loss)
        reward = abs(request.take_profit - entry)
        if risk <= 0:
            return self._result(passed=False, message="risk distance must be positive")
        ratio = reward / risk
        minimum = context.limits.min_reward_risk_ratio
        if ratio < minimum:
            return self._result(
                passed=False,
                message="risk/reward ratio below the configured minimum",
                current=ratio,
                limit=minimum,
            )
        return self._result(
            passed=True,
            message="risk/reward acceptable",
            severity=RuleSeverity.INFO,
            current=ratio,
            limit=minimum,
        )


class ConfidenceRule(RiskRule):
    key = "strategy_confidence"
    order = 150

    def evaluate(self, context: RiskContext) -> RuleResult:
        confidence = context.request.strategy_confidence
        minimum = context.limits.min_strategy_confidence
        if confidence is None:
            if context.limits.require_strategy_signal:
                return self._result(passed=False, message="a strategy signal is required")
            return self._result(
                passed=True,
                message="no strategy signal supplied (not required)",
                severity=RuleSeverity.INFO,
            )
        if confidence < minimum:
            return self._result(
                passed=False,
                message="strategy confidence below the configured minimum",
                current=confidence,
                limit=minimum,
            )
        return self._result(
            passed=True,
            message="strategy confidence acceptable",
            severity=RuleSeverity.INFO,
            current=confidence,
            limit=minimum,
        )
