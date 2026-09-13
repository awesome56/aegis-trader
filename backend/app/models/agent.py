"""AI agent run and decision models."""

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
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import MONEY, Base, JSONType, TimestampMixin, UUIDMixin
from app.models.enums import AgentMode, MarketRegime, OrderAction, RunStatus


class AgentRun(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "agent_runs"
    __table_args__ = (
        Index("ix_agent_runs_user_created", "user_id", "created_at"),
        Index("ix_agent_runs_status_created", "status", "created_at"),
    )

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    provider_config_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("ai_provider_configs.id", ondelete="SET NULL")
    )
    agent_name: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    status: Mapped[RunStatus] = mapped_column(
        Enum(RunStatus, native_enum=False), default=RunStatus.PENDING, nullable=False
    )
    provider: Mapped[str | None] = mapped_column(String(32))
    model: Mapped[str | None] = mapped_column(String(128))
    mode: Mapped[AgentMode] = mapped_column(
        Enum(AgentMode, native_enum=False), default=AgentMode.ANALYSIS_ONLY, nullable=False
    )
    prompt: Mapped[str | None] = mapped_column(Text)
    symbols: Mapped[list | None] = mapped_column(JSONType)
    context: Mapped[dict | None] = mapped_column(JSONType)
    usage: Mapped[dict | None] = mapped_column(JSONType)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    proposal_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("trade_proposals.id", ondelete="SET NULL"), index=True
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    tokens_used: Mapped[int | None] = mapped_column(Integer)
    error: Mapped[str | None] = mapped_column(Text)

    decisions: Mapped[list[AgentDecision]] = relationship(
        back_populates="agent_run", cascade="all, delete-orphan"
    )


class AgentDecision(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "agent_decisions"

    agent_run_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("agent_runs.id", ondelete="SET NULL"), index=True
    )
    portfolio_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("portfolios.id", ondelete="SET NULL"), index=True
    )
    proposal_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("trade_proposals.id", ondelete="SET NULL"), index=True
    )

    symbol: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    action: Mapped[OrderAction] = mapped_column(
        Enum(OrderAction, native_enum=False), nullable=False
    )
    confidence: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    reasoning_summary: Mapped[str | None] = mapped_column(Text)
    evidence: Mapped[list | None] = mapped_column(JSONType)
    concerns: Mapped[list | None] = mapped_column(JSONType)
    proposal_recommended: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    market_regime: Mapped[MarketRegime | None] = mapped_column(
        Enum(MarketRegime, native_enum=False)
    )
    strategy_signal_ids: Mapped[list | None] = mapped_column(JSONType)

    agent_run: Mapped[AgentRun | None] = relationship(back_populates="decisions")

    __table_args__ = (Index("ix_agent_decisions_symbol_created", "symbol", "created_at"),)
