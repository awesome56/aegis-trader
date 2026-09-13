"""Auto-trading policy (Phase 10).

Answers *may the agent act automatically?* — not *is the trade financially
permitted?* (that remains the RiskEngine's job).
"""

from __future__ import annotations

import uuid

from sqlalchemy import Boolean, Enum, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, JSONType, TimestampMixin, UUIDMixin
from app.models.enums import BrokerEnvironment


class AutoTradingPolicy(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "auto_trading_policies"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    broker_account_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("broker_accounts.id", ondelete="CASCADE"), index=True
    )
    environment: Mapped[BrokerEnvironment] = mapped_column(
        Enum(BrokerEnvironment, native_enum=False), nullable=False
    )

    enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    allow_open: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    allow_add: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    allow_reduce: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    allow_close: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    allow_cancel: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    allow_replace: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    allow_manage_manual_positions: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    allow_manage_manual_orders: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )

    allowed_asset_classes: Mapped[list | None] = mapped_column(JSONType)
    allowed_symbols: Mapped[list | None] = mapped_column(JSONType)

    # Policy-level guardrails (advisory caps; RiskEngine remains authoritative).
    max_trade_notional: Mapped[object | None] = mapped_column(Numeric(28, 10))
    max_position_notional: Mapped[object | None] = mapped_column(Numeric(28, 10))
    max_trades_per_day: Mapped[int | None] = mapped_column(Integer)
    cooldown_seconds: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    min_agent_confidence: Mapped[object | None] = mapped_column(Numeric(6, 4))
    require_strategy_signal: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    min_strategy_confidence: Mapped[object | None] = mapped_column(Numeric(6, 4))

    notes: Mapped[str | None] = mapped_column(String(500))
