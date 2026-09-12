"""Strongly typed, provider-independent market-data domain objects.

These are the only market-data shapes the rest of the application consumes.
Raw provider dictionaries never cross this boundary. Prices use ``Decimal``;
timestamps are validated as timezone-aware.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, field_validator, model_validator

from app.market.enums import MarketSession, ProviderStatus, Timeframe
from app.models.enums import AssetClass


class _DomainModel(BaseModel):
    model_config = ConfigDict(frozen=True)


class MarketQuote(_DomainModel):
    """A point-in-time quote. ``market_timestamp`` is the exchange/provider time,
    which is authoritative for freshness; ``received_at`` is when we obtained it.
    """

    symbol: str
    asset_id: uuid.UUID | None = None
    bid: Decimal | None = None
    ask: Decimal | None = None
    last: Decimal
    open: Decimal | None = None
    high: Decimal | None = None
    low: Decimal | None = None
    previous_close: Decimal | None = None
    volume: int | None = None
    currency: str = "USD"
    provider: str
    market_timestamp: AwareDatetime
    received_at: AwareDatetime

    @field_validator("symbol")
    @classmethod
    def _normalise_symbol(cls, value: str) -> str:
        return value.strip().upper()


class Candle(_DomainModel):
    """An OHLCV candle. ``provider`` records the most recent source, but candles
    are keyed by (symbol, timeframe, open_time) so providers cannot duplicate."""

    symbol: str
    asset_id: uuid.UUID | None = None
    timeframe: Timeframe
    open_time: AwareDatetime
    close_time: AwareDatetime | None = None
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int | None = None
    trade_count: int | None = None
    vwap: Decimal | None = None
    provider: str

    @field_validator("symbol")
    @classmethod
    def _normalise_symbol(cls, value: str) -> str:
        return value.strip().upper()

    @model_validator(mode="after")
    def _default_close_time(self) -> Candle:
        if self.close_time is None:
            object.__setattr__(self, "close_time", self.open_time + self.timeframe.duration)
        return self


class MarketStatus(_DomainModel):
    market: str = "EQUITIES"
    is_open: bool
    session: MarketSession
    opens_at: datetime | None = None
    closes_at: datetime | None = None
    timestamp: AwareDatetime
    provider: str


class AssetSearchResult(_DomainModel):
    symbol: str
    name: str | None = None
    asset_class: AssetClass = AssetClass.EQUITY
    exchange: str | None = None
    currency: str = "USD"
    provider: str

    @field_validator("symbol")
    @classmethod
    def _normalise_symbol(cls, value: str) -> str:
        return value.strip().upper()


class ProviderHealth(_DomainModel):
    provider: str
    status: ProviderStatus
    latency_ms: float | None = None
    detail: str | None = None
    checked_at: AwareDatetime


class FreshnessAssessment(_DomainModel):
    """Authoritative staleness verdict produced by the freshness service."""

    kind: Literal["quote", "candle"]
    symbol: str
    market_timestamp: AwareDatetime
    age_seconds: float
    max_age_seconds: int
    is_stale: bool
