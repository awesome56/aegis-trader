"""Strategy and strategy-signal models."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import MONEY, Base, JSONType, TimestampMixin, UUIDMixin
from app.models.enums import MarketRegime, SignalDirection, StrategyType, TimeHorizon


class Strategy(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "strategies"

    name: Mapped[str] = mapped_column(String(128), nullable=False)
    slug: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    strategy_type: Mapped[StrategyType] = mapped_column(
        Enum(StrategyType, native_enum=False), nullable=False
    )
    description: Mapped[str | None] = mapped_column(Text)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    timeframe: Mapped[str] = mapped_column(String(16), default="1d", nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    max_open_positions: Mapped[int | None] = mapped_column(Integer)
    parameters: Mapped[dict | None] = mapped_column(JSONType)
    asset_classes: Mapped[list | None] = mapped_column(JSONType)

    signals: Mapped[list[StrategySignal]] = relationship(
        back_populates="strategy", cascade="all, delete-orphan"
    )


class StrategySignal(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "strategy_signals"

    strategy_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("strategies.id", ondelete="CASCADE"), index=True, nullable=False
    )
    asset_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("assets.id", ondelete="SET NULL"), index=True
    )
    symbol: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    direction: Mapped[SignalDirection] = mapped_column(
        Enum(SignalDirection, native_enum=False), nullable=False
    )
    strength: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    confidence: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    price: Mapped[Decimal | None] = mapped_column(MONEY)
    timeframe: Mapped[str] = mapped_column(String(16), nullable=False)
    time_horizon: Mapped[TimeHorizon | None] = mapped_column(Enum(TimeHorizon, native_enum=False))
    market_regime: Mapped[MarketRegime | None] = mapped_column(
        Enum(MarketRegime, native_enum=False)
    )
    indicators: Mapped[dict | None] = mapped_column(JSONType)
    signal_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), index=True, nullable=False
    )
    data_timestamp: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)

    strategy: Mapped[Strategy] = relationship(back_populates="signals")

    __table_args__ = (
        Index("ix_strategy_signals_symbol_signal_time", "symbol", "signal_time"),
        Index("ix_strategy_signals_strategy_signal_time", "strategy_id", "signal_time"),
        UniqueConstraint(
            "strategy_id",
            "symbol",
            "timeframe",
            "direction",
            "data_timestamp",
            name="uq_strategy_signals_dedupe",
        ),
    )
