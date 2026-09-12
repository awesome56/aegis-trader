"""Individual risk rule tests (pure, deterministic)."""

from __future__ import annotations

from decimal import Decimal

from app.models.enums import TradeSide, TradingState
from app.risk.enums import RuleSeverity
from app.risk.rules.capital import (
    BuyingPowerRule,
    ConfidenceRule,
    RewardRiskRule,
    StopLossRule,
)
from app.risk.rules.exposure import (
    AssetClassExposureRule,
    OpenPositionsRule,
    PortfolioExposureRule,
    PositionLimitRule,
    SectorExposureRule,
)
from app.risk.rules.loss import DailyLossRule, DrawdownRule, TradeFrequencyRule
from app.risk.rules.system import MarketFreshnessRule, RequestValidityRule, TradingStateRule

from tests.risk.conftest import buy_request, risk_context, risk_limits, sample_quote


def test_trading_state_rule() -> None:
    assert TradingStateRule().evaluate(risk_context()).passed is True
    blocked = TradingStateRule().evaluate(risk_context(trading_state=TradingState.EMERGENCY_STOP))
    assert blocked.passed is False
    assert blocked.severity is RuleSeverity.BLOCKING


def test_market_freshness_rule() -> None:
    assert MarketFreshnessRule().evaluate(risk_context(quote=None)).passed is False
    stale = MarketFreshnessRule().evaluate(risk_context(quote=sample_quote(), quote_is_stale=True))
    assert stale.passed is False
    fresh = MarketFreshnessRule().evaluate(risk_context(quote=sample_quote(), quote_is_stale=False))
    assert fresh.passed is True


def test_request_validity_rule() -> None:
    assert RequestValidityRule().evaluate(risk_context()).passed is True
    bad_stop = RequestValidityRule().evaluate(
        risk_context(request=buy_request(entry_price=Decimal("100"), stop_loss=Decimal("101")))
    )
    assert bad_stop.passed is False


def test_buying_power_rule() -> None:
    ok = BuyingPowerRule().evaluate(risk_context(size_caps={"buying_power": Decimal("50")}))
    assert ok.passed is True
    reduced = BuyingPowerRule().evaluate(risk_context(size_caps={"buying_power": Decimal("5")}))
    assert reduced.passed is False and reduced.severity is RuleSeverity.WARNING
    blocked = BuyingPowerRule().evaluate(risk_context(size_caps={"buying_power": Decimal("0")}))
    assert blocked.severity is RuleSeverity.BLOCKING


def test_stop_loss_rule() -> None:
    assert StopLossRule().evaluate(risk_context()).passed is True
    missing = StopLossRule().evaluate(risk_context(request=buy_request(stop_loss=None)))
    assert missing.passed is False
    not_required = StopLossRule().evaluate(
        risk_context(
            request=buy_request(stop_loss=None), limits=risk_limits(require_stop_loss=False)
        )
    )
    assert not_required.passed is True


def test_reward_risk_rule() -> None:
    assert RewardRiskRule().evaluate(risk_context()).passed is True
    poor = RewardRiskRule().evaluate(
        risk_context(
            request=buy_request(
                entry_price=Decimal("100"), stop_loss=Decimal("99"), take_profit=Decimal("101")
            )
        )
    )
    assert poor.passed is False
    no_target = RewardRiskRule().evaluate(risk_context(request=buy_request(take_profit=None)))
    assert no_target.passed is True


def test_confidence_rule() -> None:
    below = ConfidenceRule().evaluate(
        risk_context(request=buy_request(strategy_confidence=Decimal("0.1")))
    )
    assert below.passed is False
    required = ConfidenceRule().evaluate(
        risk_context(limits=risk_limits(require_strategy_signal=True))
    )
    assert required.passed is False
    ok = ConfidenceRule().evaluate(
        risk_context(request=buy_request(strategy_confidence=Decimal("0.9")))
    )
    assert ok.passed is True


def test_position_and_exposure_rules() -> None:
    assert (
        PositionLimitRule().evaluate(risk_context(size_caps={"max_position": Decimal("20")})).passed
        is True
    )
    reduced = PositionLimitRule().evaluate(risk_context(size_caps={"max_position": Decimal("5")}))
    assert reduced.severity is RuleSeverity.WARNING
    blocked = PositionLimitRule().evaluate(risk_context(size_caps={"max_position": Decimal("0")}))
    assert blocked.severity is RuleSeverity.BLOCKING
    assert (
        PortfolioExposureRule()
        .evaluate(risk_context(size_caps={"max_portfolio_exposure": Decimal("100")}))
        .passed
        is True
    )


def test_open_positions_rule() -> None:
    at_limit = OpenPositionsRule().evaluate(
        risk_context(open_positions=10, limits=risk_limits(max_open_positions=10))
    )
    assert at_limit.passed is False
    existing = OpenPositionsRule().evaluate(
        risk_context(open_positions=10, has_existing_position=True)
    )
    assert existing.passed is True


def test_sector_and_asset_class_rules() -> None:
    unknown_reject = SectorExposureRule().evaluate(
        risk_context(sector=None, limits=risk_limits(unknown_sector_policy="reject"))
    )
    assert unknown_reject.passed is False
    unknown_warn = SectorExposureRule().evaluate(
        risk_context(sector=None, limits=risk_limits(unknown_sector_policy="warn"))
    )
    assert unknown_warn.passed is True and unknown_warn.severity is RuleSeverity.WARNING
    assert (
        AssetClassExposureRule()
        .evaluate(risk_context(size_caps={"max_asset_class_exposure": Decimal("100")}))
        .passed
        is True
    )


def test_loss_rules() -> None:
    assert DailyLossRule().evaluate(risk_context(daily_pnl=None)).severity is RuleSeverity.WARNING
    assert DailyLossRule().evaluate(risk_context(daily_pnl=Decimal("-100"))).passed is True
    assert DailyLossRule().evaluate(risk_context(daily_pnl=Decimal("-5000"))).passed is False
    assert DrawdownRule().evaluate(risk_context(drawdown_percent=Decimal("-5"))).passed is True
    assert DrawdownRule().evaluate(risk_context(drawdown_percent=Decimal("-20"))).passed is False
    assert (
        TradeFrequencyRule()
        .evaluate(risk_context(trades_today=20, limits=risk_limits(max_trades_per_day=20)))
        .passed
        is False
    )
    assert TradeFrequencyRule().evaluate(risk_context(trades_today=3)).passed is True


def test_sell_side_short_circuits_exposure_rules() -> None:
    context = risk_context(request=buy_request(side=TradeSide.SELL))
    assert PositionLimitRule().evaluate(context).passed is True
    assert PortfolioExposureRule().evaluate(context).passed is True
