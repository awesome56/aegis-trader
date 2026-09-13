"""Kraken public market-data provider (crypto, keyless).

Uses Kraken's public REST endpoints so crypto data is available without any API
key or KYC. Trading is out of scope for this provider.
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
    ProviderRateLimitError,
    ProviderUnavailableError,
)
from app.market.providers.base import MarketDataProvider
from app.market.validation import external_symbol, to_decimal
from app.models.enums import AssetClass

_INTERVAL_MINUTES = {
    Timeframe.ONE_MINUTE: 1,
    Timeframe.FIVE_MINUTES: 5,
    Timeframe.FIFTEEN_MINUTES: 15,
    Timeframe.THIRTY_MINUTES: 30,
    Timeframe.ONE_HOUR: 60,
    Timeframe.FOUR_HOURS: 240,
    Timeframe.ONE_DAY: 1440,
    Timeframe.ONE_WEEK: 10080,
}


class KrakenProvider(MarketDataProvider):
    name = "kraken"

    def __init__(
        self, settings: Settings | None = None, *, client: httpx.AsyncClient | None = None
    ) -> None:
        self._settings = settings or get_settings()
        self._base = self._settings.KRAKEN_BASE_URL.rstrip("/")
        self._client = client

    async def _get(self, path: str, params: dict) -> dict:
        try:
            if self._client is not None:
                response = await self._client.get(f"{self._base}{path}", params=params)
            else:
                async with httpx.AsyncClient(
                    timeout=self._settings.MARKET_HTTP_TIMEOUT_SECONDS
                ) as client:
                    response = await client.get(f"{self._base}{path}", params=params)
        except httpx.HTTPError as exc:
            raise ProviderUnavailableError("Kraken is unreachable") from exc
        if response.status_code == 429:
            raise ProviderRateLimitError("Kraken rate limit reached")
        if response.status_code >= 500:
            raise ProviderUnavailableError(f"Kraken error ({response.status_code})")
        payload = response.json()
        errors = payload.get("error") or []
        if errors:
            message = "; ".join(str(e) for e in errors)
            if "Unknown asset pair" in message or "EQuery" in message:
                raise AssetNotFoundError(message)
            if "Too many" in message or "rate" in message.lower():
                raise ProviderRateLimitError(message)
            raise InvalidMarketDataError(message)
        return payload.get("result") or {}

    @staticmethod
    def _first_result(result: dict):
        for key, value in result.items():
            if key == "last":
                continue
            return value
        raise AssetNotFoundError("Kraken returned no data for the pair")

    async def get_quote(self, symbol: str) -> MarketQuote:
        wire = external_symbol(symbol, self.name)
        result = await self._get("/0/public/Ticker", {"pair": wire})
        row = self._first_result(result)
        last = to_decimal(row["c"][0])
        return MarketQuote(
            symbol=symbol.strip().upper(),
            bid=to_decimal(row["b"][0]) if row.get("b") else None,
            ask=to_decimal(row["a"][0]) if row.get("a") else None,
            last=last,
            open=to_decimal(row["o"]) if row.get("o") else None,
            high=to_decimal(row["h"][1]) if row.get("h") else None,
            low=to_decimal(row["l"][1]) if row.get("l") else None,
            previous_close=None,
            volume=int(float(row["v"][1])) if row.get("v") else None,
            currency=self._settings.MARKET_DEFAULT_CURRENCY,
            provider=self.name,
            market_timestamp=datetime.now(UTC),
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
        candles = await self.get_latest_candles(symbol, timeframe, limit or 200)
        return [
            candle
            for candle in candles
            if start.astimezone(UTC) <= candle.open_time <= end.astimezone(UTC)
        ]

    async def get_latest_candles(
        self, symbol: str, timeframe: Timeframe, limit: int
    ) -> list[Candle]:
        if timeframe not in _INTERVAL_MINUTES:
            raise InvalidMarketDataError(f"Unsupported timeframe for Kraken: {timeframe}")
        wire = external_symbol(symbol, self.name)
        result = await self._get(
            "/0/public/OHLC", {"pair": wire, "interval": _INTERVAL_MINUTES[timeframe]}
        )
        rows = self._first_result(result)
        if not isinstance(rows, list):
            raise AssetNotFoundError(f"No candles for {symbol}")
        candles: list[Candle] = []
        for row in rows:
            candle = _candle(symbol, timeframe, row, self.name)
            if candle is not None:
                candles.append(candle)
        candles.sort(key=lambda candle: candle.open_time)
        return candles[-limit:]

    async def get_market_status(self) -> MarketStatus:
        return MarketStatus(
            market="CRYPTO",
            is_open=True,
            session=MarketSession.REGULAR,
            timestamp=datetime.now(UTC),
            provider=self.name,
        )

    async def search_assets(self, query: str) -> list[AssetSearchResult]:
        result = await self._get("/0/public/AssetPairs", {})
        term = query.strip().upper()
        out: list[AssetSearchResult] = []
        for row in result.values():
            if not isinstance(row, dict):
                continue
            wsname = str(row.get("wsname", ""))
            altname = str(row.get("altname", ""))
            if term not in wsname.upper() and term not in altname.upper():
                continue
            internal = wsname.replace("XBT", "BTC").upper()
            out.append(
                AssetSearchResult(
                    symbol=internal,
                    name=altname,
                    asset_class=AssetClass.CRYPTO,
                    exchange="KRAKEN",
                    currency=str(row.get("quote") or "USD"),
                    provider=self.name,
                )
            )
            if len(out) >= 25:
                break
        return out

    async def health_check(self) -> ProviderHealth:
        started = datetime.now(UTC)
        try:
            await self._get("/0/public/Time", {})
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


def _candle(
    symbol: str, timeframe: Timeframe, row: list, provider: str
) -> Candle | None:
    if not isinstance(row, list) or len(row) < 7:
        return None
    try:
        opened = datetime.fromtimestamp(int(row[0]), tz=UTC)
    except (ValueError, TypeError):
        return None
    return Candle(
        symbol=symbol.strip().upper(),
        timeframe=timeframe,
        open_time=opened,
        close_time=opened + timeframe.duration,
        open=to_decimal(row[1]),
        high=to_decimal(row[2]),
        low=to_decimal(row[3]),
        close=to_decimal(row[4]),
        volume=int(float(row[6])),
        provider=provider,
    )
