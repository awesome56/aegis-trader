"""Market data models (quotes and candles)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import MONEY, Base, TimestampMixin, UUIDMixin


class MarketQuote(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "market_quotes"

    symbol: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    bid: Mapped[object | None] = mapped_column(MONEY)
    ask: Mapped[object | None] = mapped_column(MONEY)
    last: Mapped[object] = mapped_column(MONEY, nullable=False)
    volume: Mapped[int | None] = mapped_column(BigInteger)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    quote_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), index=True, nullable=False
    )

    __table_args__ = (Index("ix_market_quotes_symbol_quote_time", "symbol", "quote_time"),)


class MarketCandle(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "market_candles"

    symbol: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    timeframe: Mapped[str] = mapped_column(String(16), nullable=False)
    open: Mapped[object] = mapped_column(MONEY, nullable=False)
    high: Mapped[object] = mapped_column(MONEY, nullable=False)
    low: Mapped[object] = mapped_column(MONEY, nullable=False)
    close: Mapped[object] = mapped_column(MONEY, nullable=False)
    volume: Mapped[int | None] = mapped_column(BigInteger)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    candle_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), index=True, nullable=False
    )

    __table_args__ = (
        UniqueConstraint(
            "symbol", "timeframe", "candle_time", name="uq_market_candles_symbol_tf_time"
        ),
    )
