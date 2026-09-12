"""Risk snapshot and per-user risk settings."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import MONEY, Base, JSONType, TimestampMixin, UUIDMixin
from app.models.enums import RiskLevel


class RiskSnapshot(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "risk_snapshots"

    portfolio_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("portfolios.id", ondelete="CASCADE"), index=True, nullable=False
    )
    snapshot_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), index=True, nullable=False
    )
    level: Mapped[RiskLevel] = mapped_column(
        Enum(RiskLevel, native_enum=False), default=RiskLevel.SAFE, nullable=False
    )
    open_positions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    trades_today: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    exposure_pct: Mapped[Decimal] = mapped_column(MONEY, default=Decimal("0"), nullable=False)
    daily_pnl: Mapped[Decimal] = mapped_column(MONEY, default=Decimal("0"), nullable=False)
    drawdown_pct: Mapped[Decimal] = mapped_column(MONEY, default=Decimal("0"), nullable=False)
    metrics: Mapped[dict | None] = mapped_column(JSONType)

    portfolio: Mapped[Portfolio] = relationship(back_populates="risk_snapshots")  # noqa: F821

    __table_args__ = (Index("ix_risk_snapshots_portfolio_time", "portfolio_id", "snapshot_time"),)


class RiskSettings(UUIDMixin, TimestampMixin, Base):
    """Per-user risk limits. Defaults are seeded from environment settings.

    This is configuration, not a point-in-time measurement (that is
    ``RiskSnapshot``); keeping them separate avoids overloading either model.
    """

    __tablename__ = "risk_settings"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True, nullable=False
    )
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    max_position_percent: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    max_portfolio_exposure_percent: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    max_open_positions: Mapped[int] = mapped_column(Integer, nullable=False)
    max_daily_loss_percent: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    max_drawdown_percent: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    max_trades_per_day: Mapped[int] = mapped_column(Integer, nullable=False)
    max_risk_per_trade_percent: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    min_strategy_confidence: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    min_reward_risk_ratio: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    require_stop_loss: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    require_strategy_signal: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    max_sector_exposure_percent: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    max_asset_class_exposure_percent: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    unknown_sector_policy: Mapped[str] = mapped_column(String(16), default="warn", nullable=False)
    daily_loss_include_unrealized: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    commission_buffer_bps: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
