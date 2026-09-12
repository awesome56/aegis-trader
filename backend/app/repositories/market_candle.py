"""Market candle repository with cross-dialect bulk upsert."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from app.market.domain.models import Candle
from app.market.enums import Timeframe
from app.market.validation import dedupe_candles
from app.models.market import MarketCandle
from app.repositories.base import BaseRepository


def _candle_row(candle: Candle) -> dict[str, object]:
    return {
        "symbol": candle.symbol,
        "asset_id": candle.asset_id,
        "timeframe": candle.timeframe.value,
        "open": candle.open,
        "high": candle.high,
        "low": candle.low,
        "close": candle.close,
        "volume": candle.volume,
        "trade_count": candle.trade_count,
        "vwap": candle.vwap,
        "provider": candle.provider,
        "candle_time": candle.open_time,
        "close_time": candle.close_time,
    }


class MarketCandleRepository(BaseRepository[MarketCandle]):
    model = MarketCandle

    def _conflict_update(self):
        """Return the dialect-appropriate upsert construct for our unique key."""
        dialect = self.session.get_bind().dialect.name
        return pg_insert if dialect == "postgresql" else sqlite_insert

    async def upsert_many(self, candles: list[Candle]) -> int:
        """Bulk upsert, de-duplicated by (symbol, timeframe, open_time).

        Returns the number of logical rows submitted. Existing rows have their
        OHLCV/provider refreshed rather than duplicated.
        """
        unique = dedupe_candles(candles)
        if not unique:
            return 0

        rows = [_candle_row(candle) for candle in unique]
        insert = self._conflict_update()(MarketCandle)
        stmt = insert.values(rows)
        stmt = stmt.on_conflict_do_update(
            index_elements=["symbol", "timeframe", "candle_time"],
            set_={
                "open": stmt.excluded.open,
                "high": stmt.excluded.high,
                "low": stmt.excluded.low,
                "close": stmt.excluded.close,
                "volume": stmt.excluded.volume,
                "trade_count": stmt.excluded.trade_count,
                "vwap": stmt.excluded.vwap,
                "provider": stmt.excluded.provider,
                "close_time": stmt.excluded.close_time,
                "asset_id": stmt.excluded.asset_id,
            },
        )
        await self.session.execute(stmt)
        await self.session.flush()
        return len(unique)

    async def get_range(
        self,
        symbol: str,
        timeframe: Timeframe,
        start: datetime | None,
        end: datetime | None,
        limit: int | None,
        *,
        ascending: bool = True,
    ) -> list[MarketCandle]:
        stmt = select(MarketCandle).where(
            MarketCandle.symbol == symbol.strip().upper(),
            MarketCandle.timeframe == timeframe.value,
        )
        if start is not None:
            stmt = stmt.where(MarketCandle.candle_time >= start)
        if end is not None:
            stmt = stmt.where(MarketCandle.candle_time <= end)

        if limit is not None and ascending:
            # Take the most recent `limit` within the range, then return ascending.
            stmt = stmt.order_by(MarketCandle.candle_time.desc()).limit(limit)
            result = await self.session.execute(stmt)
            return list(reversed(result.scalars().all()))

        stmt = stmt.order_by(
            MarketCandle.candle_time.asc() if ascending else MarketCandle.candle_time.desc()
        )
        if limit is not None:
            stmt = stmt.limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
