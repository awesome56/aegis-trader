"""Trade read API schemas (completed round trips; populated from Phase 7 onward)."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.models.enums import TradeSide


class TradeSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    symbol: str
    side: TradeSide
    quantity: Decimal
    entry_price: Decimal
    exit_price: Decimal | None
    pnl: Decimal
    fees: Decimal
    return_pct: Decimal
    strategy_id: uuid.UUID | None
    proposal_id: uuid.UUID | None
    order_id: uuid.UUID | None
    opened_at: datetime
    closed_at: datetime | None


class TradePageSchema(BaseModel):
    items: list[TradeSchema]
    total: int
    page: int
    page_size: int
