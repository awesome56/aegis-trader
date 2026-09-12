"""Trade proposal and risk evaluation models.

A ``TradeProposal`` is the *only* thing an AI agent is allowed to create. The
``RiskEvaluation`` is the deterministic verdict that must approve it before any
order can exist.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import MONEY, Base, JSONType, TimestampMixin, UUIDMixin
from app.models.enums import (
    AssetClass,
    MarketRegime,
    OrderAction,
    OrderType,
    ProposalSource,
    ProposalStatus,
    RiskDecision,
    TimeHorizon,
    TradeSide,
)


class TradeProposal(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "trade_proposals"

    portfolio_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("portfolios.id", ondelete="SET NULL"), index=True
    )
    strategy_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("strategies.id", ondelete="SET NULL"), index=True
    )
    strategy_signal_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("strategy_signals.id", ondelete="SET NULL"), index=True
    )
    agent_run_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("agent_runs.id", ondelete="SET NULL"), index=True
    )

    symbol: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    asset_class: Mapped[AssetClass] = mapped_column(
        Enum(AssetClass, native_enum=False), nullable=False
    )
    action: Mapped[OrderAction] = mapped_column(
        Enum(OrderAction, native_enum=False), nullable=False
    )
    order_type: Mapped[OrderType] = mapped_column(
        Enum(OrderType, native_enum=False), default=OrderType.MARKET, nullable=False
    )
    source: Mapped[ProposalSource] = mapped_column(
        Enum(ProposalSource, native_enum=False), default=ProposalSource.MANUAL, nullable=False
    )
    status: Mapped[ProposalStatus] = mapped_column(
        Enum(ProposalStatus, native_enum=False),
        default=ProposalStatus.PENDING,
        nullable=False,
        index=True,
    )

    proposed_quantity: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    proposed_position_percentage: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    requested_notional: Mapped[Decimal | None] = mapped_column(MONEY)
    entry_price: Mapped[Decimal | None] = mapped_column(MONEY)
    limit_price: Mapped[Decimal | None] = mapped_column(MONEY)
    stop_price: Mapped[Decimal | None] = mapped_column(MONEY)
    stop_loss: Mapped[Decimal | None] = mapped_column(MONEY)
    take_profit: Mapped[Decimal | None] = mapped_column(MONEY)

    confidence: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    time_horizon: Mapped[TimeHorizon] = mapped_column(
        Enum(TimeHorizon, native_enum=False), nullable=False
    )

    # Concise decision evidence only - never hidden chain-of-thought.
    reasoning_summary: Mapped[str | None] = mapped_column(Text)
    signals: Mapped[list | None] = mapped_column(JSONType)
    market_context: Mapped[dict | None] = mapped_column(JSONType)
    market_regime: Mapped[MarketRegime | None] = mapped_column(
        Enum(MarketRegime, native_enum=False)
    )

    idempotency_key: Mapped[str | None] = mapped_column(String(128))
    failure_reason: Mapped[str | None] = mapped_column(Text)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    executed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    portfolio: Mapped[Portfolio | None] = relationship()  # noqa: F821
    evaluations: Mapped[list[RiskEvaluation]] = relationship(
        back_populates="proposal", cascade="all, delete-orphan"
    )
    orders: Mapped[list[Order]] = relationship(back_populates="proposal")  # noqa: F821

    __table_args__ = (
        Index("ix_trade_proposals_status_created", "status", "created_at"),
        Index(
            "uq_trade_proposals_idempotency_key",
            "idempotency_key",
            unique=True,
        ),
    )


class RiskEvaluation(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "risk_evaluations"

    # Nullable: the deterministic Risk Engine can evaluate a hypothetical request
    # before a TradeProposal exists (Phase 7 adapts proposals into RiskRequests).
    proposal_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("trade_proposals.id", ondelete="CASCADE"), index=True
    )
    portfolio_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("portfolios.id", ondelete="SET NULL"), index=True
    )
    strategy_signal_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("strategy_signals.id", ondelete="SET NULL"), index=True
    )
    decision: Mapped[RiskDecision] = mapped_column(
        Enum(RiskDecision, native_enum=False), nullable=False, index=True
    )
    source: Mapped[str] = mapped_column(String(32), default="manual", nullable=False)

    symbol: Mapped[str | None] = mapped_column(String(32), index=True)
    side: Mapped[TradeSide | None] = mapped_column(Enum(TradeSide, native_enum=False))
    requested_quantity: Mapped[Decimal | None] = mapped_column(MONEY)
    requested_notional: Mapped[Decimal | None] = mapped_column(MONEY)
    entry_price: Mapped[Decimal | None] = mapped_column(MONEY)
    stop_loss: Mapped[Decimal | None] = mapped_column(MONEY)
    take_profit: Mapped[Decimal | None] = mapped_column(MONEY)
    estimated_risk_amount: Mapped[Decimal | None] = mapped_column(MONEY)

    risk_score: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    approved_quantity: Mapped[Decimal | None] = mapped_column(MONEY)
    approved_notional: Mapped[Decimal | None] = mapped_column(MONEY)
    approved_position_percentage: Mapped[Decimal | None] = mapped_column(MONEY)
    risk_reward_ratio: Mapped[Decimal | None] = mapped_column(MONEY)
    portfolio_exposure_before_pct: Mapped[Decimal | None] = mapped_column(MONEY)
    portfolio_exposure_after_pct: Mapped[Decimal | None] = mapped_column(MONEY)

    checks: Mapped[list | None] = mapped_column(JSONType)
    reasons: Mapped[list | None] = mapped_column(JSONType)
    warnings: Mapped[list | None] = mapped_column(JSONType)
    settings_snapshot: Mapped[dict | None] = mapped_column(JSONType)

    evaluated_by: Mapped[str] = mapped_column(String(64), default="risk_engine", nullable=False)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    proposal: Mapped[TradeProposal | None] = relationship(back_populates="evaluations")
