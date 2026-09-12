"""Portfolio read models returned by :class:`PortfolioService`.

These are the shapes REST clients (Nuxt/Flutter) consume. All money is
``Decimal``; percentages are expressed in percent units (e.g. ``1.24`` == 1.24%).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class _ReadModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class PortfolioSummary(_ReadModel):
    portfolio_id: uuid.UUID
    currency: str
    equity: Decimal
    cash: Decimal
    buying_power: Decimal
    invested_amount: Decimal
    market_value: Decimal
    realized_pnl: Decimal
    unrealized_pnl: Decimal
    total_pnl: Decimal
    daily_pnl: Decimal | None = None
    daily_return_percent: Decimal | None = None
    total_return_percent: Decimal
    exposure_percent: Decimal
    position_count: int
    initial_capital: Decimal
    updated_at: datetime | None = None


class PositionValuation(_ReadModel):
    id: uuid.UUID
    symbol: str
    asset_name: str | None = None
    asset_class: str | None = None
    sector: str | None = None
    quantity: Decimal
    average_entry_price: Decimal
    current_price: Decimal | None = None
    market_value: Decimal
    cost_basis: Decimal
    weight_percent: Decimal
    unrealized_pnl: Decimal
    unrealized_return_percent: Decimal
    realized_pnl: Decimal
    opened_at: datetime
    updated_at: datetime | None = None
    price_timestamp: datetime | None = None
    price_stale: bool = False


class AllocationSlice(_ReadModel):
    label: str
    value: Decimal
    weight_percent: Decimal


class AllocationBreakdown(_ReadModel):
    total_equity: Decimal
    cash_weight_percent: Decimal
    by_symbol: list[AllocationSlice]
    by_asset_class: list[AllocationSlice]
    by_sector: list[AllocationSlice]


class SnapshotPoint(_ReadModel):
    snapshot_time: datetime
    equity: Decimal
    cash: Decimal
    market_value: Decimal
    realized_pnl: Decimal
    unrealized_pnl: Decimal
    total_return_percent: Decimal
    daily_pnl: Decimal
    exposure_percent: Decimal
    position_count: int


class PortfolioHistory(_ReadModel):
    range: str
    start: datetime | None = None
    end: datetime | None = None
    point_count: int
    downsampled: bool
    drawdown_percent: Decimal
    points: list[SnapshotPoint]
