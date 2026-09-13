"""Pure, decimal-safe execution-cost helpers for backtesting.

Kept deliberately independent of the broker layer (backtesting must not depend
on live broker code). Assumptions are explicit and documented:

- ``slippage_pct`` is applied against the trade direction (buys fill higher,
  sells fill lower).
- ``fees_pct`` is charged on notional on both entry and exit.
"""

from __future__ import annotations

from decimal import Decimal

HUNDRED = Decimal("100")


def apply_slippage(price: Decimal, *, side: str, slippage_pct: Decimal) -> Decimal:
    if slippage_pct <= 0:
        return price
    factor = slippage_pct / HUNDRED
    if side.upper() == "BUY":
        return price * (Decimal("1") + factor)
    return price * (Decimal("1") - factor)


def commission_for(notional: Decimal, fees_pct: Decimal) -> Decimal:
    if fees_pct <= 0 or notional <= 0:
        return Decimal("0")
    return (notional * fees_pct / HUNDRED).quantize(Decimal("0.0000000001"))
