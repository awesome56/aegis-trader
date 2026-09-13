"""Market-data API schemas (read-only). Freshness is always server-authoritative:
clients never infer staleness from undocumented thresholds.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.market.domain.models import (
    AssetSearchResult,
    Candle,
    FreshnessAssessment,
    MarketQuote,
    MarketStatus,
)
from app.market.enums import MarketSession, ProviderStatus


class _Schema(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class QuoteSchema(_Schema):
    symbol: str
    bid: Decimal | None
    ask: Decimal | None
    last: Decimal
    open: Decimal | None
    high: Decimal | None
    low: Decimal | None
    previous_close: Decimal | None
    volume: int | None
    currency: str
    provider: str
    market_timestamp: datetime
    received_at: datetime
    age_seconds: float
    is_stale: bool

    @classmethod
    def from_domain(cls, quote: MarketQuote, freshness: FreshnessAssessment) -> QuoteSchema:
        return cls(
            symbol=quote.symbol,
            bid=quote.bid,
            ask=quote.ask,
            last=quote.last,
            open=quote.open,
            high=quote.high,
            low=quote.low,
            previous_close=quote.previous_close,
            volume=quote.volume,
            currency=quote.currency,
            provider=quote.provider,
            market_timestamp=quote.market_timestamp,
            received_at=quote.received_at,
            age_seconds=round(freshness.age_seconds, 3),
            is_stale=freshness.is_stale,
        )


class CandleSchema(_Schema):
    open_time: datetime
    close_time: datetime | None
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int | None
    trade_count: int | None
    vwap: Decimal | None

    @classmethod
    def from_domain(cls, candle: Candle) -> CandleSchema:
        return cls(
            open_time=candle.open_time,
            close_time=candle.close_time,
            open=candle.open,
            high=candle.high,
            low=candle.low,
            close=candle.close,
            volume=candle.volume,
            trade_count=candle.trade_count,
            vwap=candle.vwap,
        )


class CandleSeriesSchema(_Schema):
    symbol: str
    timeframe: str
    provider: str
    candles: list[CandleSchema]
    is_stale: bool | None = None
    age_seconds: float | None = None


class MarketStatusSchema(_Schema):
    market: str
    is_open: bool
    session: MarketSession
    opens_at: datetime | None
    closes_at: datetime | None
    timestamp: datetime
    provider: str

    @classmethod
    def from_domain(cls, status: MarketStatus) -> MarketStatusSchema:
        return cls(
            market=status.market,
            is_open=status.is_open,
            session=status.session,
            opens_at=status.opens_at,
            closes_at=status.closes_at,
            timestamp=status.timestamp,
            provider=status.provider,
        )


class AssetSearchSchema(_Schema):
    symbol: str
    name: str | None
    asset_class: str
    exchange: str | None
    currency: str
    provider: str

    @classmethod
    def from_domain(cls, result: AssetSearchResult) -> AssetSearchSchema:
        return cls(
            symbol=result.symbol,
            name=result.name,
            asset_class=result.asset_class.value,
            exchange=result.exchange,
            currency=result.currency,
            provider=result.provider,
        )


class ProviderHealthSchema(_Schema):
    provider: str
    status: ProviderStatus
    latency_ms: float | None
    detail: str | None
    checked_at: datetime


class MarketOverviewItemSchema(_Schema):
    symbol: str
    name: str | None = None
    price: Decimal | None = None
    bid: Decimal | None = None
    ask: Decimal | None = None
    previous_close: Decimal | None = None
    change: Decimal | None = None
    change_pct: Decimal | None = None
    day_high: Decimal | None = None
    day_low: Decimal | None = None
    volume: int | None = None
    signal_direction: str | None = None
    strategy: str | None = None
    confidence: Decimal | None = None
    market_regime: str | None = None
    quote_time: datetime | None = None
    age_seconds: float | None = None
    is_stale: bool = False


class MarketOverviewSchema(_Schema):
    status: MarketStatusSchema
    provider: str
    is_open: bool
    session: str
    as_of: datetime
    items: list[MarketOverviewItemSchema]
