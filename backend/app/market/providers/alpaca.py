"""Alpaca market-data provider (US equities / ETFs).

Why this provider exists: equities were priced from the mock feed while orders
executed at a real venue, so the RiskEngine and the broker disagreed on price.
Pricing equities from the **same venue that executes** removes that class of bug
by construction.

Authentication uses an Alpaca key pair (``ALPACA_DATA_API_KEY`` /
``ALPACA_DATA_API_SECRET``). The free ``iex`` feed is real-time for US equities
and its quota is far larger than Twelve Data's free tier, which the platform
exhausted in a single day.

Trading is out of scope here: this module only reads market data, and it lives in
the market layer (it must never import ``app.brokers``).
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation

import httpx

from app.core.config import Settings, get_settings
from app.market.domain.models import (
    AssetSearchResult,
    Candle,
    MarketQuote,
    MarketStatus,
    ProviderHealth,
)
from app.market.enums import MarketSession, ProviderStatus, Timeframe
from app.market.exceptions import (
    AssetNotFoundError,
    InvalidMarketDataError,
    ProviderAuthenticationError,
    ProviderRateLimitError,
    ProviderUnavailableError,
)
from app.market.providers.base import MarketDataProvider
from app.market.sessions import is_market_open, session_label
from app.market.validation import external_symbol
from app.models.enums import AssetClass

# Alpaca bar timeframes. ``4h`` has no native interval: it is aggregated from
# 1-hour bars so a configured 4h strategy does not silently fail.
_ALPACA_TIMEFRAME = {
    Timeframe.ONE_MINUTE: "1Min",
    Timeframe.FIVE_MINUTES: "5Min",
    Timeframe.FIFTEEN_MINUTES: "15Min",
    Timeframe.THIRTY_MINUTES: "30Min",
    Timeframe.ONE_HOUR: "1Hour",
    Timeframe.ONE_DAY: "1Day",
    Timeframe.ONE_WEEK: "1Week",
}
_AGGREGATE_4H_FROM = Timeframe.ONE_HOUR
_AGGREGATE_4H_BARS = 4


class AlpacaMarketDataProvider(MarketDataProvider):
    name = "alpaca"

    def __init__(
        self, settings: Settings | None = None, *, client: httpx.AsyncClient | None = None
    ) -> None:
        self._settings = settings or get_settings()
        self._base = self._settings.ALPACA_DATA_BASE_URL.rstrip("/")
        self._feed = self._settings.ALPACA_DATA_FEED
        self._key = self._settings.ALPACA_DATA_API_KEY
        self._secret = self._settings.ALPACA_DATA_API_SECRET
        self._client = client

    # --- transport ----------------------------------------------------------
    @property
    def _headers(self) -> dict[str, str]:
        return {
            "APCA-API-KEY-ID": self._key,
            "APCA-API-SECRET-KEY": self._secret,
            "Accept": "application/json",
        }

    async def _get(self, path: str, params: dict) -> dict:
        if not self._key or not self._secret:
            raise ProviderAuthenticationError(
                "Alpaca market data requires ALPACA_DATA_API_KEY/ALPACA_DATA_API_SECRET"
            )
        request_params = {**params, "feed": self._feed}
        try:
            if self._client is not None:
                response = await self._client.get(
                    f"{self._base}{path}", params=request_params, headers=self._headers
                )
            else:
                async with httpx.AsyncClient(
                    timeout=self._settings.MARKET_HTTP_TIMEOUT_SECONDS
                ) as client:
                    response = await client.get(
                        f"{self._base}{path}", params=request_params, headers=self._headers
                    )
        except httpx.HTTPError as exc:
            raise ProviderUnavailableError("Alpaca market data is unreachable") from exc
        if response.status_code in (401, 403):
            raise ProviderAuthenticationError("Alpaca market data rejected the credentials")
        if response.status_code == 404:
            raise AssetNotFoundError("Alpaca has no data for this symbol")
        if response.status_code == 422:
            raise InvalidMarketDataError(f"Alpaca rejected the request ({response.status_code})")
        if response.status_code == 429:
            raise ProviderRateLimitError("Alpaca market data rate limit reached")
        if response.status_code >= 500:
            raise ProviderUnavailableError(f"Alpaca market data error ({response.status_code})")
        try:
            payload = response.json()
        except ValueError as exc:
            raise InvalidMarketDataError("Alpaca returned a malformed response") from exc
        if not isinstance(payload, dict):
            raise InvalidMarketDataError("Alpaca returned a malformed payload")
        return payload

    # --- quotes -------------------------------------------------------------
    async def get_quote(self, symbol: str) -> MarketQuote:
        wire = external_symbol(symbol, self.name)
        payload = await self._get(f"/v2/stocks/{wire}/snapshot", {})
        return _quote_from_snapshot(symbol, payload, self.name)

    async def get_quotes(self, symbols: list[str]) -> list[MarketQuote]:
        return [await self.get_quote(symbol) for symbol in symbols]

    # --- candles ------------------------------------------------------------
    async def get_latest_candles(
        self, symbol: str, timeframe: Timeframe, limit: int
    ) -> list[Candle]:
        if timeframe is Timeframe.FOUR_HOURS:
            raw = await self._bars(symbol, Timeframe.ONE_HOUR, limit * _AGGREGATE_4H_BARS)
            return _aggregate(raw, timeframe, _AGGREGATE_4H_BARS)[-limit:]
        return await self._bars(symbol, timeframe, limit)

    async def get_candles(
        self,
        symbol: str,
        timeframe: Timeframe,
        start: datetime,
        end: datetime,
        limit: int | None = None,
    ) -> list[Candle]:
        candles = await self.get_latest_candles(symbol, timeframe, limit or 200)
        start_utc = start.astimezone(UTC)
        end_utc = end.astimezone(UTC)
        return [c for c in candles if start_utc <= c.open_time <= end_utc]

    async def _bars(self, symbol: str, timeframe: Timeframe, limit: int) -> list[Candle]:
        interval = _ALPACA_TIMEFRAME.get(timeframe)
        if interval is None:
            raise InvalidMarketDataError(f"Unsupported timeframe for Alpaca: {timeframe}")
        wire = external_symbol(symbol, self.name)
        payload = await self._get(
            f"/v2/stocks/{wire}/bars",
            {"timeframe": interval, "limit": max(1, limit), "adjustment": "raw", "sort": "asc"},
        )
        rows = payload.get("bars") or []
        if not rows:
            raise AssetNotFoundError(f"Alpaca returned no candles for {symbol}")
        candles: list[Candle] = []
        for row in rows:
            candle = _candle(symbol, timeframe, row, self.name)
            if candle is not None:
                candles.append(candle)
        candles.sort(key=lambda candle: candle.open_time)
        return candles

    # --- status / search / health -------------------------------------------
    async def get_market_status(self) -> MarketStatus:
        now = datetime.now(UTC)
        return MarketStatus(
            market="EQUITIES",
            is_open=is_market_open(AssetClass.EQUITY, now),
            session=(
                MarketSession.REGULAR
                if session_label(AssetClass.EQUITY, now) == "OPEN"
                else MarketSession.CLOSED
            ),
            timestamp=now,
            provider=self.name,
        )

    async def search_assets(self, query: str) -> list[AssetSearchResult]:
        # Alpaca's assets endpoint lives on the trading API; the symbol universe
        # is static and small, so search is served locally instead of spending a
        # data request.
        term = query.strip().upper()
        if not term:
            return []
        symbol = external_symbol(term, self.name)
        if len(symbol) > 8 or not symbol.isalnum():
            return []
        return [
            AssetSearchResult(
                symbol=symbol,
                name=symbol,
                asset_class=AssetClass.EQUITY,
                exchange="US",
                currency=self._settings.MARKET_DEFAULT_CURRENCY,
                provider=self.name,
            )
        ]

    async def health_check(self) -> ProviderHealth:
        started = datetime.now(UTC)
        try:
            await self.get_quote(self._settings.MARKET_SYMBOLS.split(",")[0] or "AAPL")
            status = ProviderStatus.CONNECTED
            detail = None
        except Exception as exc:  # noqa: BLE001 - health must never raise
            status = ProviderStatus.DISCONNECTED
            detail = str(exc)
        return ProviderHealth(
            provider=self.name,
            status=status,
            latency_ms=(datetime.now(UTC) - started).total_seconds() * 1000,
            detail=detail,
            checked_at=datetime.now(UTC),
        )


# --- pure mappers -----------------------------------------------------------
def _dec(value: object) -> Decimal | None:
    """Alpaca sends numbers as strings (and sometimes numbers); never guess."""
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def _timestamp(value: object) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    text = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)


def _quote_from_snapshot(symbol: str, payload: dict, provider: str) -> MarketQuote:
    """Map an Alpaca stock snapshot into a :class:`MarketQuote`."""
    quote = payload.get("latestQuote") or {}
    trade = payload.get("latestTrade") or {}
    daily = payload.get("dailyBar") or {}
    previous = payload.get("prevDailyBar") or {}

    bid = _dec(quote.get("bp"))
    ask = _dec(quote.get("ap"))
    last = _dec(trade.get("p")) or _dec(daily.get("c"))
    if last is None and bid is not None and ask is not None:
        last = (bid + ask) / 2
    if last is None or last <= 0:
        raise AssetNotFoundError(f"Alpaca returned no usable price for {symbol}")

    market_timestamp = (
        _timestamp(quote.get("t"))
        or _timestamp(trade.get("t"))
        or _timestamp(daily.get("t"))
        or datetime.now(UTC)
    )
    volume = daily.get("v")
    return MarketQuote(
        symbol=symbol.strip().upper(),
        bid=bid,
        ask=ask,
        last=last,
        open=_dec(daily.get("o")),
        high=_dec(daily.get("h")),
        low=_dec(daily.get("l")),
        previous_close=_dec(previous.get("c")),
        volume=int(volume) if volume is not None else None,
        currency="USD",
        provider=provider,
        market_timestamp=market_timestamp,
        received_at=datetime.now(UTC),
    )


def _candle(symbol: str, timeframe: Timeframe, row: dict, provider: str) -> Candle | None:
    open_time = _timestamp(row.get("t"))
    if open_time is None:
        return None
    open_price = _dec(row.get("o"))
    high = _dec(row.get("h"))
    low = _dec(row.get("l"))
    close = _dec(row.get("c"))
    if open_price is None or high is None or low is None or close is None:
        return None
    volume = row.get("v")
    return Candle(
        symbol=symbol.strip().upper(),
        timeframe=timeframe,
        open_time=open_time,
        open=open_price,
        high=high,
        low=low,
        close=close,
        volume=int(volume) if volume is not None else None,
        trade_count=int(row["n"]) if row.get("n") is not None else None,
        vwap=_dec(row.get("vw")),
        provider=provider,
    )


def _aggregate(candles: list[Candle], timeframe: Timeframe, size: int) -> list[Candle]:
    """Group ``size`` consecutive lower-timeframe candles into one."""
    out: list[Candle] = []
    for index in range(0, len(candles) - size + 1, size):
        chunk = candles[index : index + size]
        volumes = [c.volume for c in chunk if c.volume is not None]
        out.append(
            Candle(
                symbol=chunk[0].symbol,
                timeframe=timeframe,
                open_time=chunk[0].open_time,
                close_time=chunk[-1].close_time,
                open=chunk[0].open,
                high=max(c.high for c in chunk),
                low=min(c.low for c in chunk),
                close=chunk[-1].close,
                volume=sum(volumes) if volumes else None,
                provider=chunk[-1].provider,
            )
        )
    return out


