"""Deterministic position sizing.

The approved size is the minimum of every applicable cap: requested size,
buying power, max position %, max portfolio exposure, sector/asset-class
exposure and stop-distance risk budget. All Decimal.
"""

from __future__ import annotations

from decimal import ROUND_FLOOR, Decimal

from app.market.domain.models import MarketQuote
from app.models.enums import TradeSide
from app.risk.types import PositionSizePlan, RiskLimitsSnapshot, RiskRequest

HUNDRED = Decimal("100")
BPS = Decimal("10000")
REDUCIBLE_CAPS = (
    "buying_power",
    "max_position",
    "max_portfolio_exposure",
    "max_sector_exposure",
    "max_asset_class_exposure",
    "max_risk_per_trade",
    "position_quantity",
)


def floor_quantity(value: Decimal) -> Decimal:
    if value <= 0:
        return Decimal("0")
    return value.to_integral_value(rounding=ROUND_FLOOR)


def resolve_entry_price(request: RiskRequest, quote: MarketQuote | None) -> Decimal | None:
    if request.entry_price is not None:
        return request.entry_price
    if quote is None:
        return None
    if request.side is TradeSide.BUY:
        return quote.ask if quote.ask is not None else quote.last
    return quote.bid if quote.bid is not None else quote.last


def requested_quantity(request: RiskRequest, entry: Decimal | None) -> Decimal:
    if request.requested_quantity is not None:
        return request.requested_quantity
    if request.requested_notional is not None and entry:
        return request.requested_notional / entry
    return Decimal("0")


def compute_caps(
    *,
    request: RiskRequest,
    limits: RiskLimitsSnapshot,
    equity: Decimal,
    buying_power: Decimal,
    portfolio_market_value: Decimal,
    symbol_exposure_value: Decimal,
    sector_exposure_value: Decimal,
    asset_class_exposure_value: Decimal,
    existing_quantity: Decimal,
    entry: Decimal | None,
) -> dict[str, Decimal]:
    if entry is None or entry <= 0 or equity <= 0:
        return {}

    caps: dict[str, Decimal] = {}
    if request.side is TradeSide.BUY:
        buffer = Decimal("1") + limits.commission_buffer_bps / BPS
        caps["buying_power"] = floor_quantity(buying_power / (entry * buffer))
        caps["max_position"] = floor_quantity(
            max(
                Decimal("0"), equity * limits.max_position_percent / HUNDRED - symbol_exposure_value
            )
            / entry
        )
        caps["max_portfolio_exposure"] = floor_quantity(
            max(
                Decimal("0"),
                equity * limits.max_portfolio_exposure_percent / HUNDRED - portfolio_market_value,
            )
            / entry
        )
        caps["max_sector_exposure"] = floor_quantity(
            max(
                Decimal("0"),
                equity * limits.max_sector_exposure_percent / HUNDRED - sector_exposure_value,
            )
            / entry
        )
        caps["max_asset_class_exposure"] = floor_quantity(
            max(
                Decimal("0"),
                equity * limits.max_asset_class_exposure_percent / HUNDRED
                - asset_class_exposure_value,
            )
            / entry
        )
        if request.stop_loss is not None:
            risk_per_unit = abs(entry - request.stop_loss)
            if risk_per_unit > 0:
                budget = equity * limits.max_risk_per_trade_percent / HUNDRED
                caps["max_risk_per_trade"] = floor_quantity(budget / risk_per_unit)
    else:
        # V1 is long-only: a SELL may only reduce an existing position.
        caps["position_quantity"] = floor_quantity(existing_quantity)
    return caps


def build_plan(
    *,
    request: RiskRequest,
    caps: dict[str, Decimal],
    entry: Decimal | None,
    equity: Decimal,
    portfolio_market_value: Decimal,
    symbol_exposure_value: Decimal,
) -> PositionSizePlan:
    requested = requested_quantity(request, entry)
    approved = requested
    binding: str | None = None
    for key in REDUCIBLE_CAPS:
        cap = caps.get(key)
        if cap is not None and cap < approved:
            approved = cap
            binding = key
    approved = floor_quantity(approved) if request.side is TradeSide.BUY else approved
    if request.side is TradeSide.SELL:
        approved = min(approved, caps.get("position_quantity", Decimal("0")))

    entry_value = entry or Decimal("0")
    if request.side is TradeSide.BUY:
        projected_symbol = symbol_exposure_value + approved * entry_value
        projected_portfolio = portfolio_market_value + approved * entry_value
    else:
        projected_symbol = max(Decimal("0"), symbol_exposure_value - approved * entry_value)
        projected_portfolio = max(Decimal("0"), portfolio_market_value - approved * entry_value)

    return PositionSizePlan(
        requested_quantity=requested,
        approved_quantity=approved,
        requested_notional=requested * entry_value,
        approved_notional=approved * entry_value,
        caps=caps,
        binding_constraint=binding,
        projected_exposure_percent=(projected_portfolio / equity * HUNDRED)
        if equity
        else Decimal("0"),
        projected_position_percent=(projected_symbol / equity * HUNDRED)
        if equity
        else Decimal("0"),
    )
