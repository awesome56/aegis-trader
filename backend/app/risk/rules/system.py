"""System-wide blocking rules: trading state, market freshness, request validity."""

from __future__ import annotations

from decimal import Decimal

from app.models.enums import TradeSide, TradingState
from app.risk.base import RiskRule
from app.risk.enums import RuleSeverity
from app.risk.sizing import requested_quantity, resolve_entry_price
from app.risk.types import RiskContext, RuleResult


class TradingStateRule(RiskRule):
    key = "trading_state"
    order = 10

    def evaluate(self, context: RiskContext) -> RuleResult:
        state = context.trading_state
        if state is TradingState.TRADING_ENABLED:
            return self._result(passed=True, message="trading enabled", severity=RuleSeverity.INFO)
        return self._result(
            passed=False,
            message=f"new trading is blocked while state is {state.value}",
            metadata={"trading_state": state.value},
        )


class MarketFreshnessRule(RiskRule):
    key = "market_freshness"
    order = 20

    def evaluate(self, context: RiskContext) -> RuleResult:
        if context.quote is None:
            return self._result(
                passed=False,
                message="market data unavailable",
                metadata={"detail": context.quote_detail},
            )
        if context.quote_is_stale:
            return self._result(
                passed=False,
                message="execution market data is stale",
                metadata={"detail": context.quote_detail},
            )
        return self._result(
            passed=True,
            message="market data is fresh",
            severity=RuleSeverity.INFO,
            current=context.quote.last,
        )


class RequestValidityRule(RiskRule):
    key = "request_validity"
    order = 30

    def evaluate(self, context: RiskContext) -> RuleResult:
        request = context.request
        entry = resolve_entry_price(request, context.quote)
        if entry is None or entry <= 0:
            return self._result(passed=False, message="entry price is unavailable")
        if request.side not in (TradeSide.BUY, TradeSide.SELL):
            return self._result(passed=False, message="invalid order side")
        if requested_quantity(request, entry) <= 0:
            return self._result(passed=False, message="requested quantity must be positive")

        if request.stop_loss is not None:
            if request.side is TradeSide.BUY and request.stop_loss >= entry:
                return self._result(
                    passed=False, message="stop loss must be below entry for a long position"
                )
            if request.side is TradeSide.SELL and request.stop_loss <= entry:
                return self._result(
                    passed=False, message="stop loss must be above entry for a short/exit"
                )
        if request.take_profit is not None:
            if request.side is TradeSide.BUY and request.take_profit <= entry:
                return self._result(
                    passed=False, message="take profit must be above entry for a long position"
                )
            if request.side is TradeSide.SELL and request.take_profit >= entry:
                return self._result(
                    passed=False, message="take profit must be below entry for a short/exit"
                )
        return self._result(
            passed=True,
            message="request is valid",
            severity=RuleSeverity.INFO,
            current=entry,
        )


_ = Decimal
