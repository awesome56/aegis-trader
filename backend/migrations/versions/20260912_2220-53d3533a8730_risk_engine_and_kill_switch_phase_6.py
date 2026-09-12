"""risk engine and kill switch phase 6

Revision ID: 53d3533a8730
Revises: c3d4e5f6a7b8
Create Date: 2026-09-12 22:20:45.540746+00:00

Adds:
- ``system_state`` (persisted kill switch)
- ``risk_settings`` (per-user configurable limits)
- ``risk_evaluations`` fields so a hypothetical ``RiskRequest`` can be evaluated
  and persisted without a TradeProposal (``proposal_id`` becomes nullable).
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "53d3533a8730"
down_revision: str | None = "c3d4e5f6a7b8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "system_state",
        sa.Column("key", sa.String(length=64), nullable=False),
        sa.Column(
            "trading_state",
            sa.Enum(
                "TRADING_ENABLED",
                "TRADING_PAUSED",
                "TRADING_DISABLED",
                "EMERGENCY_STOP",
                name="tradingstate",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "previous_state",
            sa.Enum(
                "TRADING_ENABLED",
                "TRADING_PAUSED",
                "TRADING_DISABLED",
                "EMERGENCY_STOP",
                name="tradingstate",
                native_enum=False,
            ),
            nullable=True,
        ),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("actor", sa.String(length=128), nullable=True),
        sa.Column("changed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_system_state")),
    )
    op.create_index(op.f("ix_system_state_created_at"), "system_state", ["created_at"])
    op.create_index(op.f("ix_system_state_key"), "system_state", ["key"], unique=True)
    op.create_index(
        op.f("ix_system_state_trading_state"), "system_state", ["trading_state"], unique=False
    )

    op.create_table(
        "risk_settings",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False),
        sa.Column("max_position_percent", sa.Numeric(precision=28, scale=10), nullable=False),
        sa.Column(
            "max_portfolio_exposure_percent", sa.Numeric(precision=28, scale=10), nullable=False
        ),
        sa.Column("max_open_positions", sa.Integer(), nullable=False),
        sa.Column("max_daily_loss_percent", sa.Numeric(precision=28, scale=10), nullable=False),
        sa.Column("max_drawdown_percent", sa.Numeric(precision=28, scale=10), nullable=False),
        sa.Column("max_trades_per_day", sa.Integer(), nullable=False),
        sa.Column(
            "max_risk_per_trade_percent", sa.Numeric(precision=28, scale=10), nullable=False
        ),
        sa.Column("min_strategy_confidence", sa.Numeric(precision=28, scale=10), nullable=False),
        sa.Column("min_reward_risk_ratio", sa.Numeric(precision=28, scale=10), nullable=False),
        sa.Column("require_stop_loss", sa.Boolean(), nullable=False),
        sa.Column("require_strategy_signal", sa.Boolean(), nullable=False),
        sa.Column(
            "max_sector_exposure_percent", sa.Numeric(precision=28, scale=10), nullable=False
        ),
        sa.Column(
            "max_asset_class_exposure_percent", sa.Numeric(precision=28, scale=10), nullable=False
        ),
        sa.Column("unknown_sector_policy", sa.String(length=16), nullable=False),
        sa.Column("daily_loss_include_unrealized", sa.Boolean(), nullable=False),
        sa.Column("commission_buffer_bps", sa.Numeric(precision=28, scale=10), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_risk_settings_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_risk_settings")),
    )
    op.create_index(op.f("ix_risk_settings_created_at"), "risk_settings", ["created_at"])
    op.create_index(op.f("ix_risk_settings_user_id"), "risk_settings", ["user_id"], unique=True)

    with op.batch_alter_table("risk_evaluations") as batch:
        batch.add_column(sa.Column("portfolio_id", sa.Uuid(), nullable=True))
        batch.add_column(sa.Column("strategy_signal_id", sa.Uuid(), nullable=True))
        batch.add_column(
            sa.Column("source", sa.String(length=32), nullable=False, server_default="manual")
        )
        batch.add_column(sa.Column("symbol", sa.String(length=32), nullable=True))
        batch.add_column(
            sa.Column("side", sa.Enum("BUY", "SELL", name="tradeside", native_enum=False), nullable=True)
        )
        batch.add_column(
            sa.Column("requested_quantity", sa.Numeric(precision=28, scale=10), nullable=True)
        )
        batch.add_column(
            sa.Column("requested_notional", sa.Numeric(precision=28, scale=10), nullable=True)
        )
        batch.add_column(sa.Column("entry_price", sa.Numeric(precision=28, scale=10), nullable=True))
        batch.add_column(sa.Column("stop_loss", sa.Numeric(precision=28, scale=10), nullable=True))
        batch.add_column(sa.Column("take_profit", sa.Numeric(precision=28, scale=10), nullable=True))
        batch.add_column(
            sa.Column("estimated_risk_amount", sa.Numeric(precision=28, scale=10), nullable=True)
        )
        batch.add_column(
            sa.Column("approved_notional", sa.Numeric(precision=28, scale=10), nullable=True)
        )
        batch.add_column(
            sa.Column(
                "portfolio_exposure_before_pct", sa.Numeric(precision=28, scale=10), nullable=True
            )
        )
        batch.add_column(
            sa.Column(
                "portfolio_exposure_after_pct", sa.Numeric(precision=28, scale=10), nullable=True
            )
        )
        batch.alter_column("proposal_id", existing_type=sa.Uuid(), nullable=True)
        batch.create_index(op.f("ix_risk_evaluations_portfolio_id"), ["portfolio_id"])
        batch.create_index(op.f("ix_risk_evaluations_strategy_signal_id"), ["strategy_signal_id"])
        batch.create_index(op.f("ix_risk_evaluations_symbol"), ["symbol"])
        batch.create_foreign_key(
            op.f("fk_risk_evaluations_portfolio_id_portfolios"),
            "portfolios",
            ["portfolio_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch.create_foreign_key(
            op.f("fk_risk_evaluations_strategy_signal_id_strategy_signals"),
            "strategy_signals",
            ["strategy_signal_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    with op.batch_alter_table("risk_evaluations") as batch:
        batch.drop_constraint(
            op.f("fk_risk_evaluations_strategy_signal_id_strategy_signals"), type_="foreignkey"
        )
        batch.drop_constraint(
            op.f("fk_risk_evaluations_portfolio_id_portfolios"), type_="foreignkey"
        )
        batch.drop_index(op.f("ix_risk_evaluations_symbol"))
        batch.drop_index(op.f("ix_risk_evaluations_strategy_signal_id"))
        batch.drop_index(op.f("ix_risk_evaluations_portfolio_id"))
        batch.alter_column("proposal_id", existing_type=sa.Uuid(), nullable=False)
        batch.drop_column("portfolio_exposure_after_pct")
        batch.drop_column("portfolio_exposure_before_pct")
        batch.drop_column("approved_notional")
        batch.drop_column("estimated_risk_amount")
        batch.drop_column("take_profit")
        batch.drop_column("stop_loss")
        batch.drop_column("entry_price")
        batch.drop_column("requested_notional")
        batch.drop_column("requested_quantity")
        batch.drop_column("side")
        batch.drop_column("symbol")
        batch.drop_column("source")
        batch.drop_column("strategy_signal_id")
        batch.drop_column("portfolio_id")

    op.drop_index(op.f("ix_risk_settings_user_id"), table_name="risk_settings")
    op.drop_index(op.f("ix_risk_settings_created_at"), table_name="risk_settings")
    op.drop_table("risk_settings")
    op.drop_index(op.f("ix_system_state_trading_state"), table_name="system_state")
    op.drop_index(op.f("ix_system_state_key"), table_name="system_state")
    op.drop_index(op.f("ix_system_state_created_at"), table_name="system_state")
    op.drop_table("system_state")
