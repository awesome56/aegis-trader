"""CSV-backed market-data provider.

Supported layouts
-----------------
1. **Directory** (recommended): one file per symbol/timeframe named
   ``{SYMBOL}_{timeframe}.csv`` (e.g. ``AAPL_1h.csv``) under
   ``CSV_MARKET_DATA_PATH``.
2. **Single file**: a CSV that includes ``symbol`` and ``timeframe`` columns.

Required columns: ``timestamp, open, high, low, close, volume``.
Optional columns: ``symbol, timeframe, trade_count, vwap``.

Naive timestamps are interpreted as UTC and logged. Malformed rows, duplicate
timestamps and impossible candles raise :class:`InvalidMarketDataError` — corrupt
market data is never silently ignored.
"""

from __future__ import annotations

import csv
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.core.config import Settings, get_settings
from app.core.logging import get_logger
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
    ProviderUnavailableError,
)
from app.market.providers.base import MarketDataProvider
from app.market.validation import to_decimal, validate_candle

logger = get_logger(__name__)

_REQUIRED_COLUMNS = ("timestamp", "open", "high", "low", "close", "volume")
_FILE_SUFFIX = ".csv"


class CsvMarketDataProvider(MarketDataProvider):
    name = "csv"

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._path = (
            Path(self._settings.CSV_MARKET_DATA_PATH).expanduser()
            if self._settings.CSV_MARKET_DATA_PATH
            else None
        )
        self._cache: dict[tuple[str, Timeframe], list[Candle]] = {}

    # --- internals ----------------------------------------------------------
    def _require_path(self) -> Path:
        if self._path is None:
            raise ProviderUnavailableError("CSV_MARKET_DATA_PATH is not configured")
        if not self._path.exists():
            raise ProviderUnavailableError(f"CSV path does not exist: {self._path}")
        return self._path

    def _file_for(self, symbol: str, timeframe: Timeframe) -> Path:
        base = self._require_path()
        if base.is_dir():
            candidate = base / f"{symbol}_{timeframe.value}{_FILE_SUFFIX}"
            if not candidate.exists():
                raise AssetNotFoundError(
                    f"No CSV file for {symbol} {timeframe.value}",
                    details={"expected_file": candidate.name},
                )
            return candidate
        return base

    def _read_rows(self, file: Path) -> list[dict[str, str]]:
        try:
            with file.open(newline="", encoding="utf-8") as handle:
                reader = csv.DictReader(handle)
                if reader.fieldnames is None:
                    raise InvalidMarketDataError(f"{file.name} has no header row")
                missing = [c for c in _REQUIRED_COLUMNS if c not in reader.fieldnames]
                if missing:
                    raise InvalidMarketDataError(
                        f"{file.name} is missing required columns: {', '.join(missing)}"
                    )
                return [dict(row) for row in reader]
        except OSError as exc:
            raise ProviderUnavailableError(f"Unable to read {file}: {exc}") from exc

    def _parse_row(
        self, row: dict[str, Any], *, row_number: int, symbol: str, timeframe: Timeframe
    ) -> Candle:
        try:
            raw_ts = str(row["timestamp"]).strip()
            parsed = datetime.fromisoformat(raw_ts)
            if parsed.tzinfo is None:
                logger.warning("csv_naive_timestamp", file_symbol=symbol, row=row_number)
                parsed = parsed.replace(tzinfo=UTC)
            open_time = parsed.astimezone(UTC)

            volume_raw = str(row.get("volume") or "").strip()
            volume = int(float(volume_raw)) if volume_raw else None
            trade_count_raw = str(row.get("trade_count") or "").strip()
            trade_count = int(float(trade_count_raw)) if trade_count_raw else None
            vwap_raw = str(row.get("vwap") or "").strip()
            vwap = to_decimal(vwap_raw) if vwap_raw else None

            candle = Candle(
                symbol=symbol,
                timeframe=timeframe,
                open_time=open_time,
                open=to_decimal(row["open"]),
                high=to_decimal(row["high"]),
                low=to_decimal(row["low"]),
                close=to_decimal(row["close"]),
                volume=volume,
                trade_count=trade_count,
                vwap=vwap,
                provider=self.name,
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise InvalidMarketDataError(
                f"Malformed CSV row {row_number}: {exc}",
                details={"row": row_number, "symbol": symbol},
            ) from exc
        return validate_candle(candle)

    def _load(self, symbol: str, timeframe: Timeframe) -> list[Candle]:
        key = (symbol, timeframe)
        if key in self._cache:
            return self._cache[key]

        file = self._file_for(symbol, timeframe)
        rows = self._read_rows(file)
        # Always filter: in single-file mode this selects symbol+timeframe; in
        # directory mode rows without those columns default to the request.
        rows = [
            row
            for row in rows
            if (str(row.get("symbol") or symbol).strip().upper() == symbol)
            and (str(row.get("timeframe") or timeframe.value).strip().lower() == timeframe.value)
        ]

        seen: set[datetime] = set()
        candles: list[Candle] = []
        for index, row in enumerate(rows, start=2):  # header is line 1
            candle = self._parse_row(row, row_number=index, symbol=symbol, timeframe=timeframe)
            if candle.open_time in seen:
                raise InvalidMarketDataError(
                    f"Duplicate timestamp {candle.open_time.isoformat()} in {file.name}"
                )
            seen.add(candle.open_time)
            candles.append(candle)

        candles.sort(key=lambda item: item.open_time)
        self._cache[key] = candles
        return candles

    def _available_timeframes(self, symbol: str) -> list[Timeframe]:
        base = self._path
        if base is None or not base.exists():
            return []
        timeframes: set[Timeframe] = set()
        if base.is_dir():
            for file in base.glob(f"{symbol}_*{_FILE_SUFFIX}"):
                raw = file.stem[len(symbol) + 1 :]
                try:
                    timeframes.add(Timeframe.parse(raw))
                except ValueError:
                    continue
        else:
            for row in self._read_rows(base):
                if str(row.get("symbol") or "").strip().upper() != symbol:
                    continue
                raw = str(row.get("timeframe") or "").strip()
                if not raw:
                    continue
                try:
                    timeframes.add(Timeframe.parse(raw))
                except ValueError:
                    continue
        return sorted(timeframes, key=lambda item: item.seconds)

    def _all_candles(self, symbol: str) -> list[Candle]:
        candles: list[Candle] = []
        for timeframe in self._available_timeframes(symbol):
            candles.extend(self._load(symbol, timeframe))
        candles.sort(key=lambda item: item.open_time)
        return candles

    # --- provider contract --------------------------------------------------
    async def get_quote(self, symbol: str) -> MarketQuote:
        normalized = symbol.strip().upper()
        candles = self._all_candles(normalized)
        if not candles:
            raise AssetNotFoundError(f"No candles available for {normalized}")

        latest = candles[-1]
        previous = next(
            (item for item in reversed(candles[:-1]) if item.timeframe == latest.timeframe),
            None,
        )
        previous_close = previous.close if previous is not None else latest.open
        timestamp = latest.close_time or latest.open_time
        spread = latest.close * to_decimal("0.0001")
        return MarketQuote(
            symbol=normalized,
            bid=to_decimal(latest.close - spread),
            ask=to_decimal(latest.close + spread),
            last=latest.close,
            open=latest.open,
            high=latest.high,
            low=latest.low,
            previous_close=previous_close,
            volume=latest.volume,
            currency=self._settings.MARKET_DEFAULT_CURRENCY,
            provider=self.name,
            market_timestamp=timestamp,
            received_at=timestamp,
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
        candles = [
            candle
            for candle in self._load(symbol.strip().upper(), timeframe)
            if start <= candle.open_time <= end
        ]
        if limit is not None:
            candles = candles[-limit:] if limit else []
        return candles

    async def get_latest_candles(
        self, symbol: str, timeframe: Timeframe, limit: int
    ) -> list[Candle]:
        candles = self._load(symbol.strip().upper(), timeframe)
        return candles[-limit:] if limit > 0 else []

    async def get_market_status(self) -> MarketStatus:
        is_open = self._settings.CSV_MARKET_DATA_IS_OPEN
        now = datetime.now(UTC).replace(microsecond=0)
        return MarketStatus(
            is_open=is_open,
            session=MarketSession.REGULAR if is_open else MarketSession.CLOSED,
            timestamp=now,
            provider=self.name,
        )

    async def search_assets(self, query: str) -> list[AssetSearchResult]:
        term = query.strip().upper()
        symbols = self._available_symbols()
        return [
            AssetSearchResult(
                symbol=symbol,
                name=symbol,
                exchange="CSV",
                currency=self._settings.MARKET_DEFAULT_CURRENCY,
                provider=self.name,
            )
            for symbol in symbols
            if not term or term in symbol
        ]

    async def health_check(self) -> ProviderHealth:
        now = datetime.now(UTC).replace(microsecond=0)
        try:
            path = self._require_path()
        except ProviderUnavailableError as exc:
            return ProviderHealth(
                provider=self.name,
                status=ProviderStatus.DISCONNECTED,
                detail=str(exc),
                checked_at=now,
            )
        return ProviderHealth(
            provider=self.name,
            status=ProviderStatus.CONNECTED,
            detail=f"CSV source: {path}",
            checked_at=now,
        )

    def _available_symbols(self) -> list[str]:
        base = self._path
        if base is None or not base.exists():
            return []
        symbols: set[str] = set()
        if base.is_dir():
            for file in base.glob(f"*{_FILE_SUFFIX}"):
                stem = file.stem
                if "_" in stem:
                    symbols.add(stem.rsplit("_", 1)[0].upper())
        else:
            for row in self._read_rows(base):
                value = str(row.get("symbol") or "").strip().upper()
                if value:
                    symbols.add(value)
        return sorted(symbols)
