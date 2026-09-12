"""MarketDataService — the single interface other backend modules use.

Flow: cache -> database -> provider -> validate -> persist -> cache -> return.
Callers never see provider details. :meth:`get_fresh_quote` and
:meth:`get_fresh_candles` are the safety contract the later Order Manager will
rely on (fail closed on stale data).
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.market.domain.models import (
    AssetSearchResult,
    Candle,
    MarketQuote,
    MarketStatus,
    ProviderHealth,
)
from app.market.enums import Timeframe
from app.market.exceptions import (
    InvalidMarketDataError,
    MarketDataError,
    StaleMarketDataError,
    UnsupportedTimeframeError,
)
from app.market.providers.base import MarketDataProvider
from app.market.providers.factory import get_market_data_provider
from app.market.services.cache import MarketDataCache
from app.market.services.freshness import MarketDataFreshnessService
from app.market.validation import dedupe_candles, normalize_symbol, validate_candle, validate_quote
from app.models.asset import Asset
from app.repositories.asset import AssetRepository
from app.repositories.market_candle import MarketCandleRepository
from app.repositories.market_quote import MarketQuoteRepository

logger = get_logger(__name__)


class MarketDataService:
    def __init__(
        self,
        session: AsyncSession | None = None,
        *,
        provider: MarketDataProvider | None = None,
        cache: MarketDataCache | None = None,
        freshness: MarketDataFreshnessService | None = None,
        settings: Settings | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._provider = provider or get_market_data_provider(self._settings)
        self._cache = cache or MarketDataCache(settings=self._settings)
        self._freshness = freshness or MarketDataFreshnessService(self._settings)
        self._assets = AssetRepository(session) if session is not None else None
        self._quotes = MarketQuoteRepository(session) if session is not None else None
        self._candles = MarketCandleRepository(session) if session is not None else None

    @property
    def provider_name(self) -> str:
        return self._provider.name

    @property
    def freshness(self) -> MarketDataFreshnessService:
        return self._freshness

    # --- quotes -------------------------------------------------------------
    async def get_quote(self, symbol: str, *, use_cache: bool = True) -> MarketQuote:
        normalized = normalize_symbol(symbol)

        if use_cache:
            cached = await self._cache.get_quote(normalized)
            if cached is not None:
                logger.debug("market_quote", symbol=normalized, source="cache")
                return cached

        quote = validate_quote(await self._provider.get_quote(normalized))
        quote = await self._attach_asset(quote)

        if self._quotes is not None:
            await self._quotes.record(quote)
        await self._cache.set_quote(quote)
        logger.info(
            "market_quote",
            symbol=normalized,
            provider=self._provider.name,
            source="provider",
            market_timestamp=quote.market_timestamp.isoformat(),
        )
        return quote

    async def get_quotes(self, symbols: list[str]) -> list[MarketQuote]:
        return [await self.get_quote(symbol) for symbol in symbols]

    async def get_latest_price(self, symbol: str) -> Decimal:
        return (await self.get_quote(symbol)).last

    async def get_fresh_quote(self, symbol: str) -> MarketQuote:
        """Return a quote guaranteed fresh enough for a trading decision.

        Raises :class:`StaleMarketDataError` (fail closed) when stale.
        """
        return self._freshness.assert_quote_fresh(await self.get_quote(symbol))

    # --- candles ------------------------------------------------------------
    async def get_candles(
        self,
        symbol: str,
        timeframe: Timeframe | str,
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int | None = None,
    ) -> list[Candle]:
        normalized = normalize_symbol(symbol)
        tf = self._parse_timeframe(timeframe)
        self._validate_limit(limit)

        if start is None and end is None and limit is not None:
            cached = await self._cache.get_candles(normalized, tf)
            if cached:
                logger.debug(
                    "market_candles", symbol=normalized, timeframe=tf.value, source="cache"
                )
                return cached[-limit:]

        if self._candles is not None:
            stored = await self._candles.get_range(normalized, tf, start, end, limit)
            if stored and len(stored) >= self._expected_count(start, end, tf, limit):
                logger.debug(
                    "market_candles", symbol=normalized, timeframe=tf.value, source="database"
                )
                return stored

        candles = await self._fetch_candles(normalized, tf, start, end, limit)
        return candles

    async def get_latest_candles(
        self, symbol: str, timeframe: Timeframe | str, limit: int
    ) -> list[Candle]:
        """Provider-first (needs the newest bars), falling back to the database."""
        normalized = normalize_symbol(symbol)
        tf = self._parse_timeframe(timeframe)
        self._validate_limit(limit)
        try:
            candles = await self._provider.get_latest_candles(normalized, tf, limit)
        except MarketDataError:
            if self._candles is not None:
                stored = await self._candles.get_range(normalized, tf, None, None, limit)
                if stored:
                    logger.warning(
                        "market_candles_provider_fallback",
                        symbol=normalized,
                        timeframe=tf.value,
                    )
                    return stored
            raise

        candles = await self._normalise_and_persist(normalized, tf, candles)
        if limit:
            candles = candles[-limit:]
        await self._cache.set_candles(normalized, tf, candles)
        return candles

    async def get_fresh_candles(
        self, symbol: str, timeframe: Timeframe | str, limit: int = 200
    ) -> list[Candle]:
        """Return candles whose most recent bar is fresh enough for trading."""
        candles = await self.get_latest_candles(symbol, timeframe, limit)
        if not candles:
            raise StaleMarketDataError(f"No candles available for {symbol}")
        self._freshness.assert_candle_fresh(candles[-1])
        return candles

    # --- status / assets / health ------------------------------------------
    async def get_market_status(self, *, use_cache: bool = True) -> MarketStatus:
        if use_cache:
            cached = await self._cache.get_status()
            if cached is not None:
                return cached
        status = await self._provider.get_market_status()
        await self._cache.set_status(status)
        return status

    async def search_assets(self, query: str, *, limit: int = 25) -> list[AssetSearchResult]:
        results = await self._provider.search_assets(query)
        return results[:limit]

    async def get_asset(self, symbol: str) -> Asset | None:
        if self._assets is None:
            return None
        return await self._assets.get_by_symbol(symbol)

    async def health(self) -> ProviderHealth:
        return await self._provider.health_check()

    # --- internals ----------------------------------------------------------
    def _parse_timeframe(self, timeframe: Timeframe | str) -> Timeframe:
        try:
            return Timeframe.parse(timeframe)
        except ValueError as exc:
            raise UnsupportedTimeframeError(str(exc)) from exc

    def _validate_limit(self, limit: int | None) -> None:
        if limit is None:
            return
        if limit <= 0:
            raise InvalidMarketDataError("limit must be greater than 0")
        if limit > self._settings.MARKET_MAX_CANDLE_LIMIT:
            raise InvalidMarketDataError(
                f"limit exceeds the maximum of {self._settings.MARKET_MAX_CANDLE_LIMIT}"
            )

    def _expected_count(
        self, start: datetime | None, end: datetime | None, timeframe: Timeframe, limit: int | None
    ) -> int:
        if start is not None and end is not None:
            span = int((end - start).total_seconds() // timeframe.seconds) + 1
            return min(span, limit) if limit else span
        return limit or 0

    async def _fetch_candles(
        self,
        symbol: str,
        timeframe: Timeframe,
        start: datetime | None,
        end: datetime | None,
        limit: int | None,
    ) -> list[Candle]:
        if start is None or end is None:
            candles = await self._provider.get_latest_candles(
                symbol, timeframe, limit or self._settings.MARKET_MAX_CANDLE_LIMIT
            )
        else:
            candles = await self._provider.get_candles(symbol, timeframe, start, end, limit)
        candles = await self._normalise_and_persist(symbol, timeframe, candles)
        if limit:
            candles = candles[-limit:]
        await self._cache.set_candles(symbol, timeframe, candles)
        return candles

    async def _normalise_and_persist(
        self, symbol: str, timeframe: Timeframe, candles: list[Candle]
    ) -> list[Candle]:
        validated = [validate_candle(candle) for candle in candles]
        deduped = dedupe_candles(validated)
        if not deduped:
            return []

        asset = await self._ensure_asset(symbol)
        asset_id = asset.id if asset is not None else None
        enriched = [candle.model_copy(update={"asset_id": asset_id}) for candle in deduped]

        if self._candles is not None:
            await self._candles.upsert_many(enriched)
        logger.info(
            "market_candles",
            symbol=symbol,
            timeframe=timeframe.value,
            provider=self._provider.name,
            source="provider",
            record_count=len(enriched),
        )
        return enriched

    async def _attach_asset(self, quote: MarketQuote) -> MarketQuote:
        asset = await self._ensure_asset(quote.symbol)
        if asset is None:
            return quote
        return quote.model_copy(update={"asset_id": asset.id})

    async def _ensure_asset(self, symbol: str) -> Asset | None:
        if self._assets is None:
            return None
        existing = await self._assets.get_by_symbol(symbol)
        if existing is not None:
            return existing

        results = await self._provider.search_assets(symbol)
        match = next((item for item in results if item.symbol == symbol), None)
        if match is None:
            match = AssetSearchResult(symbol=symbol, provider=self._provider.name)
        return await self._assets.get_or_create_from_result(match)
