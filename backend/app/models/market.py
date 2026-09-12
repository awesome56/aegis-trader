"""Market data models (quotes and candles)."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import MONEY, Base, TimestampMixin, UUIDMixin


class MarketQuote(UUIDMixin, TimestampMixin, Base):
    """A quote snapshot record.

    Stored as a time-series (history of snapshots) consistent with the existing
    ``(symbol, quote_time)`` index; the repository only appends newer snapshots.
    """

    __tablename__ = "market_quotes"

    symbol: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    asset_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("assets.id", ondelete="SET NULL"), index=True
    )
    bid: Mapped[Decimal | None] = mapped_column(MONEY)
    ask: Mapped[Decimal | None] = mapped_column(MONEY)
    last: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    open: Mapped[Decimal | None] = mapped_column(MONEY)
    high: Mapped[Decimal | None] = mapped_column(MONEY)
    low: Mapped[Decimal | None] = mapped_column(MONEY)
    previous_close: Mapped[Decimal | None] = mapped_column(MONEY)
    volume: Mapped[int | None] = mapped_column(BigInteger)
    currency: Mapped[str] = mapped_column(String(8), default="USD", nullable=False)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    quote_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), index=True, nullable=False
    )

    __table_args__ = (Index("ix_market_quotes_symbol_quote_time", "symbol", "quote_time"),)


class MarketCandle(UUIDMixin, TimestampMixin, Base):
    """An OHLCV candle.

    Uniqueness is (symbol, timeframe, candle_time) **without** provider so the
    same logical candle cannot be duplicated across providers; ``provider``
    records the most recent source.
    """

    __tablename__ = "market_candles"

    symbol: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    asset_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("assets.id", ondelete="SET NULL"), index=True
    )
    timeframe: Mapped[str] = mapped_column(String(16), nullable=False)
    open: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    high: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    low: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    close: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    volume: Mapped[int | None] = mapped_column(BigInteger)
    trade_count: Mapped[int | None] = mapped_column(BigInteger)
    vwap: Mapped[Decimal | None] = mapped_column(MONEY)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    candle_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), index=True, nullable=False
    )
    close_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        UniqueConstraint(
            "symbol", "timeframe", "candle_time", name="uq_market_candles_symbol_tf_time"
        ),
    )
