"""Authoritative broker-side accounting.

Every financial transformation used by the paper broker lives here exactly once,
so cash, cost basis, commission and P&L cannot drift between call sites. All
arithmetic is ``Decimal``; the storage quantum matches ``MONEY`` (28,10).
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

from app.models.enums import TradeSide

MONEY_QUANTUM = Decimal("0.0000000001")
BPS_DENOMINATOR = Decimal("10000")


def q(value: Decimal) -> Decimal:
    """Quantise a monetary value to the storage precision."""
    return value.quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)


def bps_factor(bps: Decimal | float | int) -> Decimal:
    return Decimal(str(bps)) / BPS_DENOMINATOR


def apply_slippage(price: Decimal, slippage_bps: Decimal | float | int, side: TradeSide) -> Decimal:
    """Worsen the price in the direction of the trade.

    BUY pays more; SELL receives less.
    """
    factor = bps_factor(slippage_bps)
    if side is TradeSide.BUY:
        return q(price * (Decimal("1") + factor))
    return q(price * (Decimal("1") - factor))


def synthetic_bid_ask(mid: Decimal, spread_bps: Decimal | float | int) -> tuple[Decimal, Decimal]:
    """Build a bid/ask around ``mid``.

    ``spread_bps`` is the **half-spread** in basis points, so the quoted spread
    is ``2 * spread_bps``. Used only when a provider quote lacks a valid bid/ask.
    """
    factor = bps_factor(spread_bps)
    bid = q(mid * (Decimal("1") - factor))
    ask = q(mid * (Decimal("1") + factor))
    return bid, ask


def commission_for(quantity: Decimal, price: Decimal, flat_fee: Decimal) -> Decimal:
    """Commission model for V1: a flat fee per execution (``BROKER_PAPER_COMMISSION``)."""
    return q(flat_fee)


def add_to_position(
    current_quantity: Decimal,
    current_basis: Decimal,
    add_quantity: Decimal,
    add_price: Decimal,
    commission: Decimal,
) -> tuple[Decimal, Decimal, Decimal]:
    """Increase a long position, folding commission into cost basis.

    Returns ``(new_quantity, new_cost_basis, new_average_entry)``.
    """
    if add_quantity <= 0:
        raise ValueError("add_quantity must be positive")
    new_quantity = current_quantity + add_quantity
    new_basis = q(current_basis + (add_price * add_quantity) + commission)
    new_average = q(new_basis / new_quantity) if new_quantity else Decimal("0")
    return new_quantity, new_basis, new_average


def reduce_position(
    current_quantity: Decimal,
    average_entry: Decimal,
    sell_quantity: Decimal,
    exit_price: Decimal,
    commission: Decimal,
) -> tuple[Decimal, Decimal, Decimal]:
    """Reduce a long position and realise P&L.

    Returns ``(new_quantity, new_cost_basis, realized_pnl)`` where
    ``realized_pnl = (exit_price - average_entry) * sell_quantity - commission``.
    """
    if sell_quantity <= 0:
        raise ValueError("sell_quantity must be positive")
    if sell_quantity > current_quantity:
        raise ValueError("sell_quantity exceeds position quantity")
    new_quantity = current_quantity - sell_quantity
    new_basis = q(average_entry * new_quantity) if new_quantity else Decimal("0")
    realized = q((exit_price - average_entry) * sell_quantity - commission)
    return new_quantity, new_basis, realized


def unrealized_pnl(quantity: Decimal, average_entry: Decimal, mark_price: Decimal) -> Decimal:
    if quantity <= 0:
        return Decimal("0")
    return q((mark_price - average_entry) * quantity)


def market_value(quantity: Decimal, mark_price: Decimal) -> Decimal:
    if quantity <= 0:
        return Decimal("0")
    return q(quantity * mark_price)


def return_percent(unrealized: Decimal, cost_basis: Decimal) -> Decimal:
    if cost_basis <= 0:
        return Decimal("0")
    return q(unrealized / cost_basis * Decimal("100"))


def percent_of(numerator: Decimal, denominator: Decimal) -> Decimal:
    if denominator == 0:
        return Decimal("0")
    return q(numerator / denominator * Decimal("100"))
