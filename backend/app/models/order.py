"""Order, execution, and round-trip trade models."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import MONEY, Base, JSONType, TimestampMixin, UUIDMixin
from app.models.enums import OrderStatus, OrderType, PositionSide, TradeSide


class Order(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "orders"

    proposal_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("trade_proposals.id", ondelete="SET NULL"), index=True
    )
    portfolio_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("portfolios.id", ondelete="CASCADE"), index=True, nullable=False
    )
    broker_account_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("broker_accounts.id", ondelete="SET NULL"), index=True
    )

    symbol: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    side: Mapped[PositionSide] = mapped_column(
        Enum(PositionSide, native_enum=False), nullable=False
    )
    order_type: Mapped[OrderType] = mapped_column(
        Enum(OrderType, native_enum=False), nullable=False
    )
    status: Mapped[OrderStatus] = mapped_column(
        Enum(OrderStatus, native_enum=False),
        default=OrderStatus.CREATED,
        nullable=False,
        index=True,
    )

    quantity: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    filled_quantity: Mapped[Decimal] = mapped_column(MONEY, default=Decimal("0"), nullable=False)
    limit_price: Mapped[Decimal | None] = mapped_column(MONEY)
    stop_price: Mapped[Decimal | None] = mapped_column(MONEY)
    average_fill_price: Mapped[Decimal | None] = mapped_column(MONEY)
    fees: Mapped[Decimal] = mapped_column(MONEY, default=Decimal("0"), nullable=False)

    # Idempotency: unique client key prevents duplicate submissions.
    idempotency_key: Mapped[str] = mapped_column(
        String(128), unique=True, index=True, nullable=False
    )
    client_order_id: Mapped[str | None] = mapped_column(String(128), index=True)
    broker_order_id: Mapped[str | None] = mapped_column(String(128), index=True)

    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    filled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_message: Mapped[str | None] = mapped_column(Text)

    raw_request: Mapped[dict | None] = mapped_column(JSONType)
    raw_response: Mapped[dict | None] = mapped_column(JSONType)

    proposal: Mapped[TradeProposal | None] = relationship(back_populates="orders")  # noqa: F821
    portfolio: Mapped[Portfolio] = relationship(back_populates="orders")  # noqa: F821
    broker_account: Mapped[BrokerAccount | None] = relationship(  # noqa: F821
        back_populates="orders"
    )
    executions: Mapped[list[Execution]] = relationship(
        back_populates="order", cascade="all, delete-orphan"
    )

    __table_args__ = (Index("ix_orders_portfolio_status", "portfolio_id", "status"),)


class Execution(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "executions"

    order_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"), index=True, nullable=False
    )
    quantity: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    price: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    fees: Mapped[Decimal] = mapped_column(MONEY, default=Decimal("0"), nullable=False)
    commission: Mapped[Decimal] = mapped_column(MONEY, default=Decimal("0"), nullable=False)
    slippage: Mapped[Decimal] = mapped_column(MONEY, default=Decimal("0"), nullable=False)
    broker_execution_id: Mapped[str | None] = mapped_column(String(128), index=True)
    liquidity: Mapped[str | None] = mapped_column(String(32))
    executed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    raw: Mapped[dict | None] = mapped_column(JSONType)

    order: Mapped[Order] = relationship(back_populates="executions")


class Trade(UUIDMixin, TimestampMixin, Base):
    """A completed round trip (open and close) for reporting/analytics."""

    __tablename__ = "trades"

    portfolio_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("portfolios.id", ondelete="CASCADE"), index=True, nullable=False
    )
    order_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("orders.id", ondelete="SET NULL"), index=True
    )
    proposal_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("trade_proposals.id", ondelete="SET NULL"), index=True
    )
    strategy_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("strategies.id", ondelete="SET NULL"), index=True
    )

    symbol: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    side: Mapped[TradeSide] = mapped_column(Enum(TradeSide, native_enum=False), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    entry_price: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    exit_price: Mapped[Decimal | None] = mapped_column(MONEY)
    pnl: Mapped[Decimal] = mapped_column(MONEY, default=Decimal("0"), nullable=False)
    fees: Mapped[Decimal] = mapped_column(MONEY, default=Decimal("0"), nullable=False)
    return_pct: Mapped[Decimal] = mapped_column(MONEY, default=Decimal("0"), nullable=False)
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    portfolio: Mapped[Portfolio] = relationship(back_populates="trades")  # noqa: F821

    __table_args__ = (Index("ix_trades_portfolio_closed", "portfolio_id", "closed_at"),)
