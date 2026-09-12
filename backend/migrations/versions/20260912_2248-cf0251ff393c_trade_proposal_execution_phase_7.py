"""trade proposal execution phase 7

Revision ID: cf0251ff393c
Revises: 53d3533a8730
Create Date: 2026-09-12 22:48:29.700147+00:00

Adds the TradeProposal execution fields (source, strategy signal link,
idempotency key, limit/stop price, failure reason, executed timestamp) and
widens the proposal status enum for the Phase 7 lifecycle.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "cf0251ff393c"
down_revision: str | None = "53d3533a8730"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_STATUS_VALUES = (
    "DRAFT",
    "PENDING",
    "PENDING_RISK",
    "RISK_APPROVED",
    "RISK_REJECTED",
    "READY_FOR_EXECUTION",
    "EXECUTING",
    "EXECUTED",
    "APPROVED",
    "REJECTED",
    "EXPIRED",
    "CANCELLED",
    "FAILED",
)


def upgrade() -> None:
    with op.batch_alter_table("trade_proposals") as batch:
        batch.add_column(sa.Column("strategy_signal_id", sa.Uuid(), nullable=True))
        batch.add_column(
            sa.Column(
                "source",
                sa.Enum("MANUAL", "STRATEGY", "AGENT", name="proposalsource", native_enum=False),
                nullable=False,
                server_default="MANUAL",
            )
        )
        batch.add_column(
            sa.Column("requested_notional", sa.Numeric(precision=28, scale=10), nullable=True)
        )
        batch.add_column(sa.Column("limit_price", sa.Numeric(precision=28, scale=10), nullable=True))
        batch.add_column(sa.Column("stop_price", sa.Numeric(precision=28, scale=10), nullable=True))
        batch.add_column(sa.Column("idempotency_key", sa.String(length=128), nullable=True))
        batch.add_column(sa.Column("failure_reason", sa.Text(), nullable=True))
        batch.add_column(sa.Column("executed_at", sa.DateTime(timezone=True), nullable=True))
        batch.alter_column(
            "status",
            existing_type=sa.VARCHAR(length=9),
            type_=sa.Enum(*_STATUS_VALUES, name="proposalstatus", native_enum=False),
            existing_nullable=False,
        )
        batch.create_index("ix_trade_proposals_strategy_signal_id", ["strategy_signal_id"])
        batch.create_index("uq_trade_proposals_idempotency_key", ["idempotency_key"], unique=True)
        batch.create_foreign_key(
            "fk_trade_proposals_strategy_signal_id_strategy_signals",
            "strategy_signals",
            ["strategy_signal_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    with op.batch_alter_table("trade_proposals") as batch:
        batch.drop_constraint(
            "fk_trade_proposals_strategy_signal_id_strategy_signals", type_="foreignkey"
        )
        batch.drop_index("uq_trade_proposals_idempotency_key")
        batch.drop_index("ix_trade_proposals_strategy_signal_id")
        batch.alter_column(
            "status",
            existing_type=sa.Enum(*_STATUS_VALUES, name="proposalstatus", native_enum=False),
            type_=sa.VARCHAR(length=9),
            existing_nullable=False,
        )
        batch.drop_column("executed_at")
        batch.drop_column("failure_reason")
        batch.drop_column("idempotency_key")
        batch.drop_column("stop_price")
        batch.drop_column("limit_price")
        batch.drop_column("requested_notional")
        batch.drop_column("source")
        batch.drop_column("strategy_signal_id")
