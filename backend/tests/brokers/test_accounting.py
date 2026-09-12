"""Pure broker accounting tests."""

from __future__ import annotations

from decimal import Decimal

import pytest
from app.brokers.accounting import (
    add_to_position,
    apply_slippage,
    commission_for,
    market_value,
    percent_of,
    reduce_position,
    return_percent,
    synthetic_bid_ask,
    unrealized_pnl,
)
from app.models.enums import TradeSide


def test_add_to_position_weighted_average() -> None:
    quantity, basis, average = add_to_position(
        Decimal("10"), Decimal("1000"), Decimal("10"), Decimal("120"), Decimal("0")
    )
    assert quantity == Decimal("20")
    assert average == Decimal("110")
    assert basis == Decimal("2200")


def test_add_to_position_folds_commission_into_basis() -> None:
    _, basis, average = add_to_position(
        Decimal("0"), Decimal("0"), Decimal("10"), Decimal("100"), Decimal("5")
    )
    assert basis == Decimal("1005")
    assert average == Decimal("100.5")


def test_reduce_position_realizes_pnl() -> None:
    quantity, basis, realized = reduce_position(
        Decimal("20"), Decimal("100"), Decimal("5"), Decimal("120"), Decimal("0")
    )
    assert quantity == Decimal("15")
    assert basis == Decimal("1500")
    assert realized == Decimal("100")


def test_reduce_position_accounts_for_sell_commission() -> None:
    _, _, realized = reduce_position(
        Decimal("10"), Decimal("100"), Decimal("10"), Decimal("110"), Decimal("2")
    )
    assert realized == Decimal("98")


def test_reduce_position_rejects_oversell() -> None:
    with pytest.raises(ValueError):
        reduce_position(Decimal("5"), Decimal("100"), Decimal("6"), Decimal("110"), Decimal("0"))


def test_slippage_direction() -> None:
    assert apply_slippage(Decimal("100"), Decimal("10"), TradeSide.BUY) == Decimal("100.1")
    assert apply_slippage(Decimal("100"), Decimal("10"), TradeSide.SELL) == Decimal("99.9")
    assert apply_slippage(Decimal("100"), Decimal("0"), TradeSide.BUY) == Decimal("100")


def test_synthetic_spread_is_half_spread() -> None:
    bid, ask = synthetic_bid_ask(Decimal("100"), Decimal("10"))
    assert bid == Decimal("99.9")
    assert ask == Decimal("100.1")


def test_commission_and_pnl_helpers() -> None:
    assert commission_for(Decimal("10"), Decimal("100"), Decimal("1.5")) == Decimal("1.5")
    assert unrealized_pnl(Decimal("10"), Decimal("100"), Decimal("110")) == Decimal("100")
    assert unrealized_pnl(Decimal("0"), Decimal("100"), Decimal("110")) == Decimal("0")
    assert market_value(Decimal("10"), Decimal("110")) == Decimal("1100")
    assert return_percent(Decimal("100"), Decimal("1000")) == Decimal("10")
    assert percent_of(Decimal("25"), Decimal("200")) == Decimal("12.5")
    assert percent_of(Decimal("10"), Decimal("0")) == Decimal("0")
