"""Market-data REST endpoints (read-only, authenticated).

Freshness fields (``age_seconds``, ``is_stale``) are computed server-side so
clients never infer staleness from undocumented thresholds.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.auth.dependencies import DbSession, get_current_user
from app.market.dependencies import IndicatorDep, MarketDataDep
from app.market.enums import Timeframe
from app.market.validation import detect_asset_class
from app.models.enums import AssetClass
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
    from app.repositories.strategy import StrategyRepository, StrategySignalRepository

    settings = get_settings()
    signals = await StrategySignalRepository(session).list_signals(limit=500)
    strategies = {row.id: row for row in await StrategyRepository(session).list_all()}
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
        change = None
        change_pct = None
        change_window = None
        last_candle_time = None
        if quote.previous_close is not None and quote.previous_close != 0:
            change = quote.last - quote.previous_close
            change_pct = change / quote.previous_close * Decimal("100")
            change_window = "prev_close"
        else:
            # Derive a clearly-labelled change from candles where the provider
            # does not expose a previous close (e.g. Kraken crypto). Crypto: 24h;
            # forex: 1d.
            asset_class = detect_asset_class(symbol)
            candle_tf, lookback, label = (
                ("1h", 25, "24h") if asset_class is AssetClass.CRYPTO else ("1d", 2, "1d")
            )
            try:
                candles = await service.get_latest_candles(symbol, candle_tf, lookback)
                if len(candles) >= lookback and candles[-lookback].close != 0:
                    comparison = candles[-lookback].close
                    change = quote.last - comparison
                    change_pct = change / comparison * Decimal("100")
                    change_window = label
                    last_candle_time = candles[-1].close_time or candles[-1].open_time
            except Exception:  # noqa: BLE001, S110 - enrichment is best-effort
                pass
        signal = latest.get(symbol)
        strategy = strategies.get(signal.strategy_id) if signal else None
        asset = await service.get_asset(symbol)
        items.append(
            MarketOverviewItemSchema(
                symbol=symbol,
                name=asset.name if asset else None,
                provider=service.routed_provider_name(symbol),
                price=quote.last,
                bid=quote.bid,
                ask=quote.ask,
                previous_close=quote.previous_close,
                change=change,
                change_pct=change_pct,
                change_window=change_window,
                day_high=quote.high,
                day_low=quote.low,
                volume=quote.volume,
                signal_direction=signal.direction.value if signal else None,
                strategy=strategy.slug if strategy else None,
                confidence=signal.confidence if signal else None,
                market_regime=signal.market_regime.value
                if signal and signal.market_regime
                else None,
                quote_time=quote.market_timestamp,
                last_candle_time=last_candle_time,
                signal_time=signal.signal_time if signal else None,
                signal_expires_at=signal.expires_at if signal else None,
                age_seconds=round(assessment.age_seconds, 3),
                is_stale=assessment.is_stale,
                market_closed=assessment.market_closed,
                session=assessment.session,
            )
        )
    status = await service.get_market_status()
    return MarketOverviewSchema(
        status=MarketStatusSchema.from_domain(status),
        provider=service.provider_name,
        is_open=status.is_open,
        session=status.session.value,
        as_of=datetime.now(UTC),
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
