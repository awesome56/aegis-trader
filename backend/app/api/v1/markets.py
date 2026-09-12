"""Market-data REST endpoints (read-only, authenticated).

Freshness fields (``age_seconds``, ``is_stale``) are computed server-side so
clients never infer staleness from undocumented thresholds.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.auth.dependencies import DbSession, get_current_user
from app.market.dependencies import IndicatorDep, MarketDataDep
from app.market.enums import Timeframe
from app.schemas.indicators import IndicatorResponseSchema
from app.schemas.market import (
    AssetSearchSchema,
    CandleSchema,
    CandleSeriesSchema,
    MarketOverviewItemSchema,
    MarketOverviewSchema,
    MarketStatusSchema,
    QuoteSchema,
)

router = APIRouter(
    prefix="/markets",
    tags=["markets"],
    dependencies=[Depends(get_current_user)],
)

_TIMEFRAME_DESCRIPTION = "Candle timeframe: " + ", ".join(member.value for member in Timeframe)


@router.get("/status", response_model=MarketStatusSchema, summary="Market session status")
async def market_status(service: MarketDataDep) -> MarketStatusSchema:
    return MarketStatusSchema.from_domain(await service.get_market_status())


@router.get("/overview", response_model=MarketOverviewSchema, summary="Watchlist overview")
async def market_overview(service: MarketDataDep, session: DbSession) -> MarketOverviewSchema:
    """Configured symbol universe with quotes and the latest strategy signal."""
    from decimal import Decimal

    from app.core.config import get_settings
    from app.repositories.strategy import StrategySignalRepository

    settings = get_settings()
    signals = await StrategySignalRepository(session).list_signals(limit=500)
    latest: dict[str, object] = {}
    for signal in signals:
        latest.setdefault(signal.symbol, signal)

    items: list[MarketOverviewItemSchema] = []
    for symbol in settings.market_symbols:
        try:
            quote = await service.get_quote(symbol)
        except Exception:  # noqa: BLE001, S112 - skip unavailable symbols
            continue
        assessment = service.freshness.assess_quote(quote)
        change_pct = None
        if quote.previous_close and quote.previous_close != 0:
            change_pct = (
                (quote.last - quote.previous_close) / quote.previous_close * Decimal("100")
            )
        signal = latest.get(symbol)
        asset = await service.get_asset(symbol)
        items.append(
            MarketOverviewItemSchema(
                symbol=symbol,
                name=asset.name if asset else None,
                price=quote.last,
                change_pct=change_pct,
                volume=quote.volume,
                signal_direction=signal.direction.value if signal else None,
                strategy=signal.strategy.slug if signal and signal.strategy else None,
                confidence=signal.confidence if signal else None,
                market_regime=signal.market_regime.value
                if signal and signal.market_regime
                else None,
                quote_time=quote.market_timestamp,
                is_stale=assessment.is_stale,
            )
        )
    return MarketOverviewSchema(
        status=MarketStatusSchema.from_domain(await service.get_market_status()),
        items=items,
    )


@router.get("/search", response_model=list[AssetSearchSchema], summary="Search assets")
async def search_assets(
    service: MarketDataDep,
    q: Annotated[str, Query(min_length=1, max_length=32, description="Symbol or name fragment")],
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
) -> list[AssetSearchSchema]:
    results = await service.search_assets(q, limit=limit)
    return [AssetSearchSchema.from_domain(result) for result in results]


@router.get("/{symbol}/quote", response_model=QuoteSchema, summary="Latest quote")
async def get_quote(symbol: str, service: MarketDataDep) -> QuoteSchema:
    quote = await service.get_quote(symbol)
    assessment = service.freshness.assess_quote(quote)
    return QuoteSchema.from_domain(quote, assessment)


@router.get("/{symbol}/candles", response_model=CandleSeriesSchema, summary="Historical candles")
async def get_candles(
    symbol: str,
    service: MarketDataDep,
    timeframe: Annotated[str, Query(description=_TIMEFRAME_DESCRIPTION)] = "1h",
    start: Annotated[datetime | None, Query(description="Inclusive start (ISO 8601)")] = None,
    end: Annotated[datetime | None, Query(description="Inclusive end (ISO 8601)")] = None,
    limit: Annotated[int, Query(ge=1, le=1000)] = 200,
) -> CandleSeriesSchema:
    candles = await service.get_candles(symbol, timeframe, start, end, limit)
    is_stale: bool | None = None
    age_seconds: float | None = None
    if candles:
        assessment = service.freshness.assess_candle(candles[-1])
        is_stale = assessment.is_stale
        age_seconds = round(assessment.age_seconds, 3)

    return CandleSeriesSchema(
        symbol=symbol.strip().upper(),
        timeframe=Timeframe.parse(timeframe).value,
        provider=candles[-1].provider if candles else service.provider_name,
        candles=[CandleSchema.from_domain(candle) for candle in candles],
        is_stale=is_stale,
        age_seconds=age_seconds,
    )


@router.get(
    "/{symbol}/indicators", response_model=IndicatorResponseSchema, summary="Technical indicators"
)
async def get_indicators(
    symbol: str,
    service: MarketDataDep,
    indicators: IndicatorDep,
    timeframe: Annotated[str, Query(description=_TIMEFRAME_DESCRIPTION)] = "1h",
    limit: Annotated[int, Query(ge=1, le=1000)] = 200,
) -> IndicatorResponseSchema:
    candles = await service.get_latest_candles(symbol, timeframe, limit)
    bundle = indicators.calculate_indicators(candles)
    age_seconds: float | None = None
    is_stale: bool | None = None
    if candles:
        assessment = service.freshness.assess_candle(candles[-1])
        age_seconds = round(assessment.age_seconds, 3)
        is_stale = assessment.is_stale
    return IndicatorResponseSchema.from_bundle(bundle, age_seconds=age_seconds, is_stale=is_stale)
