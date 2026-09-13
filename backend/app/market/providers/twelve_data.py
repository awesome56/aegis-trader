"""Twelve Data provider (equities + forex + crypto) via REST.

Requires ``TWELVE_DATA_API_KEY``. Normalises Twelve Data's responses into the
platform's :class:`Candle` / :class:`MarketQuote` contract so no provider
payloads leak into strategy or agent code.
"""

from __future__ import annotations

from datetime import UTC, datetime

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
from app.market.validation import detect_asset_class, external_symbol, to_decimal

_INTERVAL = {
    Timeframe.ONE_MINUTE: "1min",
    Timeframe.FIVE_MINUTES: "5min",
    Timeframe.FIFTEEN_MINUTES: "15min",
    Timeframe.THIRTY_MINUTES: "30min",
    Timeframe.ONE_HOUR: "1h",
    Timeframe.FOUR_HOURS: "4h",
    Timeframe.ONE_DAY: "1day",
    Timeframe.ONE_WEEK: "1week",
}


class TwelveDataProvider(MarketDataProvider):
    name = "twelvedata"

    def __init__(
        self, settings: Settings | None = None, *, client: httpx.AsyncClient | None = None
    ) -> None:
        self._settings = settings or get_settings()
        self._base = self._settings.TWELVE_DATA_BASE_URL.rstrip("/")
        self._key = self._settings.TWELVE_DATA_API_KEY
        self._client = client

    # --- transport ----------------------------------------------------------
    async def _get(self, path: str, params: dict) -> dict:
        if not self._key:
            raise ProviderAuthenticationError("TWELVE_DATA_API_KEY is not configured")
        params = {**params, "apikey": self._key}
        try:
            if self._client is not None:
                response = await self._client.get(f"{self._base}{path}", params=params)
            else:
                async with httpx.AsyncClient(
                    timeout=self._settings.MARKET_HTTP_TIMEOUT_SECONDS
                ) as client:
                    response = await client.get(f"{self._base}{path}", params=params)
        except httpx.HTTPError as exc:
            raise ProviderUnavailableError("Twelve Data is unreachable") from exc

        if response.status_code in (401, 403):
            raise ProviderAuthenticationError("Twelve Data rejected the API key")
        if response.status_code == 429:
            raise ProviderRateLimitError("Twelve Data rate limit reached")
        if response.status_code >= 500:
            raise ProviderUnavailableError(f"Twelve Data error ({response.status_code})")
        payload = response.json()
        if isinstance(payload, dict) and payload.get("status") == "error":
            code = payload.get("code")
            message = str(payload.get("message", "provider error"))
            if code in (401, 403) or "api key" in message.lower():
                raise ProviderAuthenticationError("Twelve Data rejected the API key")
            if code == 429:
                raise ProviderRateLimitError("Twelve Data rate limit reached")
            if code == 404 or "not found" in message.lower():
                raise AssetNotFoundError(message)
            raise InvalidMarketDataError(message)
        return payload

    # --- domain -------------------------------------------------------------
    async def get_quote(self, symbol: str) -> MarketQuote:
        wire = external_symbol(symbol, self.name)
        payload = await self._get("/quote", {"symbol": wire})
        if not isinstance(payload, dict) or "close" not in payload:
            raise AssetNotFoundError(f"No quote for {symbol}")
        close = to_decimal(payload["close"])
        previous = to_decimal(payload["previous_close"]) if payload.get("previous_close") else None
        timestamp = _parse_datetime(payload.get("datetime")) or datetime.now(UTC)
        return MarketQuote(
            symbol=symbol.strip().upper(),
            bid=to_decimal(payload["bid"]) if payload.get("bid") else None,
            ask=to_decimal(payload["ask"]) if payload.get("ask") else None,
            last=close,
            open=to_decimal(payload["open"]) if payload.get("open") else None,
            high=to_decimal(payload["high"]) if payload.get("high") else None,
            low=to_decimal(payload["low"]) if payload.get("low") else None,
            previous_close=previous,
            volume=int(payload["volume"]) if payload.get("volume") else None,
            currency=str(payload.get("currency") or self._settings.MARKET_DEFAULT_CURRENCY),
            provider=self.name,
            market_timestamp=timestamp,
            received_at=datetime.now(UTC),
        )

    async def get_quotes(self, symbols: list[str]) -> list[MarketQuote]:
        return [await self.get_quote(symbol) for symbol in symbols]

    async def get_candles(
        self,
        symbol: str,
        timeframe: Timeframe,
        start: datetime,
        end: datetime,
        limit: int | None = None,
    ) -> list[Candle]:
        wire = external_symbol(symbol, self.name)
        outputsize = min(max(limit or 200, 1), self._settings.MARKET_MAX_CANDLE_LIMIT)
        payload = await self._get(
            "/time_series",
            {
                "symbol": wire,
                "interval": _INTERVAL[timeframe],
                "outputsize": outputsize,
                "order": "ASC",
                "start_date": start.astimezone(UTC).strftime("%Y-%m-%d %H:%M:%S"),
                "end_date": end.astimezone(UTC).strftime("%Y-%m-%d %H:%M:%S"),
            },
        )
        return _candles(symbol, timeframe, payload, self.name)

    async def get_latest_candles(
        self, symbol: str, timeframe: Timeframe, limit: int
    ) -> list[Candle]:
        wire = external_symbol(symbol, self.name)
        outputsize = min(max(limit, 1), self._settings.MARKET_MAX_CANDLE_LIMIT)
        payload = await self._get(
            "/time_series",
            {
                "symbol": wire,
                "interval": _INTERVAL[timeframe],
                "outputsize": outputsize,
                "order": "ASC",
            },
        )
        candles = _candles(symbol, timeframe, payload, self.name)
        return candles[-limit:]

    async def get_market_status(self) -> MarketStatus:
        now = datetime.now(UTC)
        is_weekday = now.weekday() < 5
        minutes = now.hour * 60 + now.minute
        is_open = is_weekday and (13 * 60 + 30) <= minutes < (20 * 60)
        return MarketStatus(
            market="US_EQUITIES",
            is_open=is_open,
            session=MarketSession.REGULAR if is_open else MarketSession.CLOSED,
            timestamp=now,
            provider=self.name,
        )

    async def search_assets(self, query: str) -> list[AssetSearchResult]:
        # Twelve Data symbol search requires a paid plan; keep it best-effort.
        try:
            payload = await self._get("/symbol_search", {"symbol": query})
        except Exception:  # noqa: BLE001 - search is optional
            return []
        results = payload.get("data", []) if isinstance(payload, dict) else []
        out: list[AssetSearchResult] = []
        for row in results[:25]:
            symbol = str(row.get("symbol", "")).upper()
            if not symbol:
                continue
            out.append(
                AssetSearchResult(
                    symbol=symbol,
                    name=row.get("instrument_name"),
                    asset_class=detect_asset_class(symbol),
                    exchange=row.get("exchange"),
                    currency=str(row.get("currency") or "USD"),
                    provider=self.name,
                )
            )
        return out

    async def health_check(self) -> ProviderHealth:
        started = datetime.now(UTC)
        try:
            await self._get("/quote", {"symbol": "AAPL"})
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


def _parse_datetime(value: object) -> datetime | None:
    if not value:
        return None
    text = str(value)
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt).replace(tzinfo=UTC)
        except ValueError:
            continue
    return None


def _candles(symbol: str, timeframe: Timeframe, payload: object, provider: str) -> list[Candle]:
    if not isinstance(payload, dict):
        raise InvalidMarketDataError("unexpected time_series payload")
    values = payload.get("values")
    if values is None:
        raise AssetNotFoundError(str(payload.get("message") or f"No candles for {symbol}"))
    out: list[Candle] = []
    for row in values:
        opened = _parse_datetime(row.get("datetime"))
        if opened is None:
            continue
        out.append(
            Candle(
                symbol=symbol.strip().upper(),
                timeframe=timeframe,
                open_time=opened,
                close_time=opened + timeframe.duration,
                open=to_decimal(row["open"]),
                high=to_decimal(row["high"]),
                low=to_decimal(row["low"]),
                close=to_decimal(row["close"]),
                volume=int(float(row["volume"])) if row.get("volume") not in (None, "") else None,
                provider=provider,
            )
        )
    out.sort(key=lambda candle: candle.open_time)
    return out
