"""Deterministic position-sizing tests."""

from __future__ import annotations

from decimal import Decimal

from app.models.enums import TradeSide
from app.risk.sizing import build_plan, compute_caps, floor_quantity, requested_quantity

from tests.risk.conftest import buy_request, risk_limits, sample_quote


def test_floor_quantity() -> None:
    assert floor_quantity(Decimal("10.9")) == Decimal("10")
    assert floor_quantity(Decimal("-1")) == Decimal("0")


def test_requested_quantity_from_notional() -> None:
    request = buy_request(requested_quantity=None, requested_notional=Decimal("1000"))
    assert requested_quantity(request, Decimal("100")) == Decimal("10")


def test_compute_caps_buy() -> None:
    caps = compute_caps(
        request=buy_request(),
        limits=risk_limits(),
        equity=Decimal("100000"),
        buying_power=Decimal("100000"),
        portfolio_market_value=Decimal("0"),
        symbol_exposure_value=Decimal("0"),
        sector_exposure_value=Decimal("0"),
        asset_class_exposure_value=Decimal("0"),
        existing_quantity=Decimal("0"),
        entry=Decimal("100"),
    )
    # 5% of 100k / 100 = 50 units; 80% / 100 = 800; buying power slightly less.
    assert caps["max_position"] == Decimal("50")
    assert caps["max_portfolio_exposure"] == Decimal("800")
    assert "max_risk_per_trade" in caps  # stop-distance budget present


def test_build_plan_binds_to_smallest_cap() -> None:
    plan = build_plan(
        request=buy_request(requested_quantity=Decimal("100")),
        caps={"max_position": Decimal("50"), "buying_power": Decimal("30")},
        entry=Decimal("100"),
        equity=Decimal("100000"),
        portfolio_market_value=Decimal("0"),
        symbol_exposure_value=Decimal("0"),
    )
    assert plan.approved_quantity == Decimal("30")
    assert plan.binding_constraint == "buying_power"
    assert plan.projected_position_percent == Decimal("3")


def test_sell_cap_is_existing_position() -> None:
    request = buy_request(side=TradeSide.SELL)
    caps = compute_caps(
        request=request,
        limits=risk_limits(),
        equity=Decimal("100000"),
        buying_power=Decimal("0"),
        portfolio_market_value=Decimal("0"),
        symbol_exposure_value=Decimal("0"),
        sector_exposure_value=Decimal("0"),
        asset_class_exposure_value=Decimal("0"),
        existing_quantity=Decimal("8"),
        entry=Decimal("100"),
    )
    plan = build_plan(
        request=request,
        caps=caps,
        entry=Decimal("100"),
        equity=Decimal("100000"),
        portfolio_market_value=Decimal("0"),
        symbol_exposure_value=Decimal("800"),
    )
    assert plan.approved_quantity == Decimal("8")
    assert plan.projected_position_percent == Decimal("0")


def test_resolve_entry_price_uses_ask_for_buy() -> None:
    from app.risk.sizing import resolve_entry_price

    quote = sample_quote(100.0)
    assert resolve_entry_price(buy_request(entry_price=None), quote) == quote.ask
