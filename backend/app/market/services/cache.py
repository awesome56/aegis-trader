"""Redis-backed market-data cache with a pluggable backend.

Cache entries always carry temporal context (provider, market timestamp,
received/cached timestamps) so staleness can be reasoned about; a bare price is
never cached. Redis failures degrade to cache misses rather than failing
requests.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Protocol, TypeVar

from pydantic import BaseModel

from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.database.redis import get_redis
from app.market.domain.models import Candle, MarketQuote, MarketStatus
from app.market.enums import Timeframe

logger = get_logger(__name__)

ModelT = TypeVar("ModelT", bound=BaseModel)


class CacheBackend(Protocol):
    async def get(self, key: str) -> str | None: ...

    async def set(self, key: str, value: str, ttl_seconds: int) -> None: ...

    async def delete(self, key: str) -> None: ...


class RedisCacheBackend:
    """Cache backend over the shared Redis client. Failures are non-fatal."""

    def __init__(self, client=None) -> None:  # type: ignore[no-untyped-def]
        self._client = client or get_redis()

    async def get(self, key: str) -> str | None:
        try:
            return await self._client.get(key)
        except Exception as exc:  # noqa: BLE001 - cache must never break requests
            logger.warning("market_cache_get_failed", key=key, error=str(exc))
            return None

    async def set(self, key: str, value: str, ttl_seconds: int) -> None:
        try:
            await self._client.set(key, value, ex=max(1, ttl_seconds))
        except Exception as exc:  # noqa: BLE001
            logger.warning("market_cache_set_failed", key=key, error=str(exc))

    async def delete(self, key: str) -> None:
        try:
            await self._client.delete(key)
        except Exception as exc:  # noqa: BLE001
            logger.warning("market_cache_delete_failed", key=key, error=str(exc))


class InMemoryCacheBackend:
    """Deterministic in-memory backend for tests and single-process fallbacks."""

    def __init__(self, clock=None) -> None:  # type: ignore[no-untyped-def]
        self._clock = clock or (lambda: datetime.now(UTC).timestamp())
        self._store: dict[str, tuple[str, float | None]] = {}

    async def get(self, key: str) -> str | None:
        entry = self._store.get(key)
        if entry is None:
            return None
        value, expires_at = entry
        if expires_at is not None and self._clock() >= expires_at:
            self._store.pop(key, None)
            return None
        return value

    async def set(self, key: str, value: str, ttl_seconds: int) -> None:
        expires_at = self._clock() + ttl_seconds if ttl_seconds > 0 else self._clock()
        self._store[key] = (value, expires_at)

    async def delete(self, key: str) -> None:
        self._store.pop(key, None)


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


class MarketDataCache:
    """Typed cache for quotes, candles and market status."""

    def __init__(
        self,
        backend: CacheBackend | None = None,
        settings: Settings | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._backend = backend or RedisCacheBackend()

    # --- keys ---------------------------------------------------------------
    def quote_key(self, symbol: str) -> str:
        return f"{self._settings.MARKET_CACHE_PREFIX}:quote:{symbol.upper()}"

    def candles_key(self, symbol: str, timeframe: Timeframe) -> str:
        return f"{self._settings.MARKET_CACHE_PREFIX}:candles:{symbol.upper()}:{timeframe.value}"

    def status_key(self) -> str:
        return f"{self._settings.MARKET_CACHE_PREFIX}:status"

    # --- quote --------------------------------------------------------------
    async def get_quote(self, symbol: str) -> MarketQuote | None:
        return await self._read_model(self.quote_key(symbol), MarketQuote)

    async def set_quote(self, quote: MarketQuote) -> None:
        await self._write_model(
            self.quote_key(quote.symbol),
            quote,
            self._settings.MARKET_QUOTE_CACHE_TTL_SECONDS,
        )

    # --- candles ------------------------------------------------------------
    async def get_candles(self, symbol: str, timeframe: Timeframe) -> list[Candle] | None:
        raw = await self._backend.get(self.candles_key(symbol, timeframe))
        if raw is None:
            return None
        try:
            payload = json.loads(raw)
            return [Candle.model_validate(item) for item in payload["data"]]
        except (KeyError, ValueError, TypeError) as exc:
            logger.warning("market_cache_decode_failed", kind="candles", error=str(exc))
            return None

    async def set_candles(self, symbol: str, timeframe: Timeframe, candles: list[Candle]) -> None:
        payload = {
            "kind": "candles",
            "provider": candles[0].provider if candles else None,
            "cached_at": _now_iso(),
            "data": [json.loads(candle.model_dump_json()) for candle in candles],
        }
        await self._backend.set(
            self.candles_key(symbol, timeframe),
            json.dumps(payload),
            self._settings.MARKET_CANDLE_CACHE_TTL_SECONDS,
        )

    # --- status -------------------------------------------------------------
    async def get_status(self) -> MarketStatus | None:
        return await self._read_model(self.status_key(), MarketStatus)

    async def set_status(self, status: MarketStatus) -> None:
        await self._write_model(
            self.status_key(), status, self._settings.MARKET_STATUS_CACHE_TTL_SECONDS
        )

    # --- helpers ------------------------------------------------------------
    async def _read_model(self, key: str, model: type[ModelT]) -> ModelT | None:
        raw = await self._backend.get(key)
        if raw is None:
            return None
        try:
            payload = json.loads(raw)
            return model.model_validate(payload["data"])
        except (KeyError, ValueError, TypeError) as exc:
            logger.warning("market_cache_decode_failed", key=key, error=str(exc))
            return None

    async def _write_model(self, key: str, value: BaseModel, ttl_seconds: int) -> None:
        payload = {
            "kind": key.split(":")[1] if ":" in key else "value",
            "provider": getattr(value, "provider", None),
            "cached_at": _now_iso(),
            "data": json.loads(value.model_dump_json()),
        }
        await self._backend.set(key, json.dumps(payload), ttl_seconds)
