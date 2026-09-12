"""Position model."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import MONEY, Base, TimestampMixin, UUIDMixin
from app.models.enums import PositionSide


class Position(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "positions"

    portfolio_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("portfolios.id", ondelete="CASCADE"), index=True, nullable=False
    )
    asset_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("assets.id", ondelete="SET NULL"), index=True
    )
    symbol: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    side: Mapped[PositionSide] = mapped_column(
        Enum(PositionSide, native_enum=False), default=PositionSide.LONG, nullable=False
    )
    quantity: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    average_entry_price: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    cost_basis: Mapped[Decimal] = mapped_column(MONEY, default=Decimal("0"), nullable=False)
    current_price: Mapped[Decimal | None] = mapped_column(MONEY)
    market_value: Mapped[Decimal] = mapped_column(MONEY, default=Decimal("0"), nullable=False)
    unrealized_pnl: Mapped[Decimal] = mapped_column(MONEY, default=Decimal("0"), nullable=False)
    realized_pnl: Mapped[Decimal] = mapped_column(MONEY, default=Decimal("0"), nullable=False)
    stop_loss: Mapped[Decimal | None] = mapped_column(MONEY)
    take_profit: Mapped[Decimal | None] = mapped_column(MONEY)
    strategy_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("strategies.id", ondelete="SET NULL"), index=True
    )
    proposal_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("trade_proposals.id", ondelete="SET NULL"), index=True
    )
    is_open: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_marked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    portfolio: Mapped[Portfolio] = relationship(back_populates="positions")  # noqa: F821
    asset: Mapped[Asset | None] = relationship(back_populates="positions")  # noqa: F821

    __table_args__ = (
        Index("ix_positions_portfolio_symbol_open", "portfolio_id", "symbol", "is_open"),
    )
