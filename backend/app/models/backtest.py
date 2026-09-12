"""Backtest and backtest-result models."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import MONEY, Base, JSONType, TimestampMixin, UUIDMixin
from app.models.enums import BacktestStatus


class Backtest(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "backtests"

    strategy_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("strategies.id", ondelete="SET NULL"), index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    symbols: Mapped[list | None] = mapped_column(JSONType)
    timeframe: Mapped[str] = mapped_column(String(16), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    initial_capital: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    benchmark_symbol: Mapped[str | None] = mapped_column(String(32))
    status: Mapped[BacktestStatus] = mapped_column(
        Enum(BacktestStatus, native_enum=False), default=BacktestStatus.PENDING, nullable=False
    )
    parameters: Mapped[dict | None] = mapped_column(JSONType)
    error: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    result: Mapped[BacktestResult | None] = relationship(
        back_populates="backtest", uselist=False, cascade="all, delete-orphan"
    )


class BacktestResult(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "backtest_results"

    backtest_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("backtests.id", ondelete="CASCADE"), unique=True, index=True, nullable=False
    )
    initial_capital: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    final_capital: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    total_return_pct: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    benchmark_return_pct: Mapped[Decimal | None] = mapped_column(MONEY)
    num_trades: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    wins: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    losses: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    win_rate: Mapped[Decimal] = mapped_column(MONEY, default=Decimal("0"), nullable=False)
    average_win: Mapped[Decimal] = mapped_column(MONEY, default=Decimal("0"), nullable=False)
    average_loss: Mapped[Decimal] = mapped_column(MONEY, default=Decimal("0"), nullable=False)
    profit_factor: Mapped[Decimal | None] = mapped_column(MONEY)
    max_drawdown_pct: Mapped[Decimal] = mapped_column(MONEY, default=Decimal("0"), nullable=False)
    sharpe_ratio: Mapped[Decimal | None] = mapped_column(MONEY)
    sortino_ratio: Mapped[Decimal | None] = mapped_column(MONEY)
    expectancy: Mapped[Decimal | None] = mapped_column(MONEY)
    exposure_pct: Mapped[Decimal | None] = mapped_column(MONEY)
    fees: Mapped[Decimal] = mapped_column(MONEY, default=Decimal("0"), nullable=False)
    slippage: Mapped[Decimal] = mapped_column(MONEY, default=Decimal("0"), nullable=False)

    equity_curve: Mapped[list | None] = mapped_column(JSONType)
    trade_history: Mapped[list | None] = mapped_column(JSONType)

    backtest: Mapped[Backtest] = relationship(back_populates="result")
