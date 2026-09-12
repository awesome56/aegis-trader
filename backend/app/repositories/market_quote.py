"""Market quote repository.

Design decision: ``market_quotes`` is a **snapshot log** (time-series), matching
the existing ``(symbol, quote_time)`` index. To avoid unbounded growth from
repeated identical fetches, :meth:`record` only inserts when the incoming quote
is newer than the latest stored snapshot for that symbol.
"""

from __future__ import annotations

from sqlalchemy import select

from app.market.domain.models import MarketQuote
from app.models.market import MarketQuote as MarketQuoteModel
from app.repositories.base import BaseRepository


class MarketQuoteRepository(BaseRepository[MarketQuoteModel]):
    model = MarketQuoteModel

    async def latest_for_symbol(self, symbol: str) -> MarketQuoteModel | None:
        stmt = (
            select(MarketQuoteModel)
            .where(MarketQuoteModel.symbol == symbol.strip().upper())
            .order_by(MarketQuoteModel.quote_time.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def record(self, quote: MarketQuote) -> MarketQuoteModel | None:
        """Persist a quote snapshot if it is newer than the stored one.

        Returns the inserted row, or ``None`` when the snapshot is not newer.
        """
        existing = await self.latest_for_symbol(quote.symbol)
        if existing is not None and existing.quote_time >= quote.market_timestamp:
            return None

        model = MarketQuoteModel(
            symbol=quote.symbol,
            asset_id=quote.asset_id,
            bid=quote.bid,
            ask=quote.ask,
            last=quote.last,
            open=quote.open,
            high=quote.high,
            low=quote.low,
            previous_close=quote.previous_close,
            volume=quote.volume,
            currency=quote.currency,
            provider=quote.provider,
            quote_time=quote.market_timestamp,
        )
        return await self.add(model)
