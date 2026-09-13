"""Deterministic mock market-data provider.

The same ``(seed, symbol, timeframe, timestamp)`` always produces the same data,
which makes tests reproducible and lets every later phase be developed without a
network dependency. No randomness is drawn from global state.
"""

from __future__ import annotations

import math
import random
import zlib
from collections.abc import Callable
from datetime import UTC, datetime
from decimal import Decimal

from app.core.config import Settings, get_settings
from app.market.domain.models import (
    AssetSearchResult,
    Candle,
    MarketQuote,
    MarketStatus,
    ProviderHealth,
)
from app.market.enums import MarketSession, ProviderStatus, Timeframe
from app.market.exceptions import AssetNotFoundError, InvalidMarketDataError
from app.market.providers import scenarios
from app.market.providers.base import MarketDataProvider
from app.market.validation import to_decimal

# Safety cap so a very wide historical request cannot allocate unbounded memory.
_MAX_GENERATED_CANDLES = 10_000

_SYMBOL_NAMES: dict[str, str] = {
    "AAPL": "Apple Inc.",
    "MSFT": "Microsoft Corporation",
    "NVDA": "NVIDIA Corporation",
    "TSLA": "Tesla, Inc.",
    "AMZN": "Amazon.com, Inc.",
    "GOOGL": "Alphabet Inc.",
    "META": "Meta Platforms, Inc.",
    "SPY": "SPDR S&P 500 ETF Trust",
}

# Regular US equity session, expressed in UTC (13:30–20:00).
_SESSION_OPEN = (13, 30)
_SESSION_CLOSE = (20, 0)


def _floor_to(dt: datetime, timeframe: Timeframe) -> datetime:
    seconds = timeframe.seconds
    epoch = int(dt.timestamp())
    floored = epoch - (epoch % seconds)
    return datetime.fromtimestamp(floored, tz=UTC)


class MockMarketDataProvider(MarketDataProvider):
    name = "mock"

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._clock = clock or (lambda: datetime.now(UTC))
        self._symbols = self._settings.market_symbols
        self._base_cache: dict[str, Decimal] = {}
        for symbol in self._symbols:
            rng = random.Random(f"{self._settings.MOCK_MARKET_SEED}:{symbol}:base")
            factor = 1 + rng.uniform(-0.25, 0.25)
            self._base_cache[symbol] = to_decimal(self._settings.MOCK_MARKET_START_PRICE * factor)

    # --- internals ----------------------------------------------------------
    def _now(self) -> datetime:
        return self._clock().astimezone(UTC).replace(microsecond=0)

    def _ensure_known(self, symbol: str) -> str:
        normalized = symbol.strip().upper()
        if normalized not in self._symbols:
            raise AssetNotFoundError(
                f"Symbol {normalized!r} is not available from the mock provider",
                details={"symbol": normalized, "available": self._symbols},
            )
        return normalized

    def _symbol_base(self) -> dict[str, Decimal]:
        return self._base_cache

    def _scenario(self) -> str | None:
        return scenarios.normalise_scenario(self._settings.MOCK_MARKET_SCENARIO)

    def _build_scenario_candles(
        self,
        symbol: str,
        timeframe: Timeframe,
        timestamps: list[datetime],
        scenario: str,
    ) -> list[Candle]:
        base = float(self._symbol_base()[symbol])
        count = len(timestamps)
        closes = scenarios.scenario_closes(scenario, count, base)
        volumes = scenarios.scenario_volumes(scenario, count)
        env = scenarios.envelope(scenario)
        candles: list[Candle] = []
        for index, open_time in enumerate(timestamps):
            close_price = closes[index]
            open_price = closes[index - 1] if index > 0 else close_price * (1 - env)
            high_price = max(open_price, close_price) * (1 + env)
            low_price = min(open_price, close_price) * (1 - env)
            candles.append(
                Candle(
                    symbol=symbol,
                    timeframe=timeframe,
                    open_time=open_time,
                    close_time=open_time + timeframe.duration,
                    open=to_decimal(open_price),
                    high=to_decimal(max(high_price, open_price, close_price)),
                    low=to_decimal(min(low_price, open_price, close_price)),
                    close=to_decimal(close_price),
                    volume=volumes[index],
                    provider=self.name,
                )
            )
        return candles

    def _build_candle(self, symbol: str, timeframe: Timeframe, open_time: datetime) -> Candle:
        volatility = self._settings.MOCK_MARKET_VOLATILITY
        index = int(open_time.timestamp()) // timeframe.seconds
        rng = random.Random(f"{self._settings.MOCK_MARKET_SEED}:{symbol}:{timeframe.value}:{index}")

        phase = (zlib.crc32(symbol.encode()) % 1000) / 1000 * 2 * math.pi
        drift = 1 + 0.2 * math.sin(index / 500 + phase)
        base = float(self._symbol_base()[symbol]) * drift

        open_price = base * (1 + rng.uniform(-volatility, volatility))
        close_price = open_price * (1 + rng.uniform(-volatility, volatility))
        high_price = max(open_price, close_price) * (1 + abs(rng.uniform(0, volatility)))
        low_price = min(open_price, close_price) * (1 - abs(rng.uniform(0, volatility)))

        o = to_decimal(open_price)
        c = to_decimal(close_price)
        h = max(to_decimal(high_price), o, c)
        low = min(to_decimal(low_price), o, c)
        volume = int(500_000 + rng.random() * 4_500_000)

        return Candle(
            symbol=symbol,
            timeframe=timeframe,
            open_time=open_time,
            close_time=open_time + timeframe.duration,
            open=o,
            high=h,
            low=low,
            close=c,
            volume=volume,
            provider=self.name,
        )

    def _generate(
        self, symbol: str, timeframe: Timeframe, start: datetime, end: datetime
    ) -> list[Candle]:
        if end < start:
            raise InvalidMarketDataError("end must be greater than or equal to start")
        aligned = _floor_to(start, timeframe)
        timestamps: list[datetime] = []
        cursor = aligned
        while cursor <= end:
            timestamps.append(cursor)
            cursor += timeframe.duration
            if len(timestamps) > _MAX_GENERATED_CANDLES:
                timestamps = timestamps[-_MAX_GENERATED_CANDLES:]
                break
        scenario = self._scenario()
        if scenario:
            return self._build_scenario_candles(symbol, timeframe, timestamps, scenario)
        return [self._build_candle(symbol, timeframe, ts) for ts in timestamps]

    # --- provider contract --------------------------------------------------
    async def get_quote(self, symbol: str) -> MarketQuote:
        normalized = self._ensure_known(symbol)
        now = self._now()
        timeframe = Timeframe.ONE_MINUTE
        scenario = self._scenario()
        if scenario:
            end = _floor_to(now, timeframe)
            timestamps = [end - timeframe.duration * (63 - index) for index in range(64)]
            series = self._build_scenario_candles(normalized, timeframe, timestamps, scenario)
            current = series[-1]
            previous = series[-2]
        else:
            current_open = _floor_to(now, timeframe)
            current = self._build_candle(normalized, timeframe, current_open)
            previous = self._build_candle(normalized, timeframe, current_open - timeframe.duration)

        spread = current.close * Decimal("0.0001")
        return MarketQuote(
            symbol=normalized,
            bid=to_decimal(current.close - spread),
            ask=to_decimal(current.close + spread),
            last=current.close,
            open=current.open,
            high=current.high,
            low=current.low,
            previous_close=previous.close,
            volume=current.volume,
            currency=self._settings.MARKET_DEFAULT_CURRENCY,
            provider=self.name,
            market_timestamp=now,
            received_at=now,
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
        normalized = self._ensure_known(symbol)
        candles = self._generate(normalized, timeframe, start, end)
        if limit is not None and limit >= 0:
            candles = candles[-limit:] if limit else []
        return candles

    async def get_latest_candles(
        self, symbol: str, timeframe: Timeframe, limit: int
    ) -> list[Candle]:
        normalized = self._ensure_known(symbol)
        if limit <= 0:
            return []
        end = _floor_to(self._now(), timeframe)
        start = end - timeframe.duration * (limit - 1)
        return self._generate(normalized, timeframe, start, end)

    async def get_market_status(self) -> MarketStatus:
        now = self._now()
        is_open = self._settings.MOCK_MARKET_IS_OPEN
        opens_at = now.replace(
            hour=_SESSION_OPEN[0], minute=_SESSION_OPEN[1], second=0, microsecond=0
        )
        closes_at = now.replace(
            hour=_SESSION_CLOSE[0], minute=_SESSION_CLOSE[1], second=0, microsecond=0
        )
        return MarketStatus(
            is_open=is_open,
            session=MarketSession.REGULAR if is_open else MarketSession.CLOSED,
            opens_at=opens_at,
            closes_at=closes_at,
            timestamp=now,
            provider=self.name,
        )

    async def search_assets(self, query: str) -> list[AssetSearchResult]:
        term = query.strip().upper()
        results: list[AssetSearchResult] = []
        for symbol in self._symbols:
            name = _SYMBOL_NAMES.get(symbol, symbol)
            if not term or term in symbol or term in name.upper():
                results.append(
                    AssetSearchResult(
                        symbol=symbol,
                        name=name,
                        exchange="MOCK",
                        currency=self._settings.MARKET_DEFAULT_CURRENCY,
                        provider=self.name,
                    )
                )
        return results

    async def health_check(self) -> ProviderHealth:
        return ProviderHealth(
            provider=self.name,
            status=ProviderStatus.MOCK,
            detail=f"deterministic mock provider ({len(self._symbols)} symbols)",
            checked_at=self._now(),
        )

    @property
    def symbol_universe(self) -> list[str]:
        return list(self._symbols)
