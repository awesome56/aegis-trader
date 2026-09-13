"""phase 10: broker environments, connections, auto-trading policy

Revision ID: a1b2c3d4e5f6
Revises: f6a7b8c9d0e1
Create Date: 2026-09-13

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: str | None = "f6a7b8c9d0e1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("broker_accounts", schema=None) as batch:
        batch.add_column(
            sa.Column(
                "environment",
                sa.Enum("DEMO", "LIVE", name="brokerenvironment", native_enum=False),
                nullable=False,
                server_default="DEMO",
            )
        )

    op.create_table(
        "broker_connections",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column(
            "environment",
            sa.Enum("DEMO", "LIVE", name="brokerenvironment", native_enum=False),
            nullable=False,
        ),
        sa.Column("account_external_id", sa.String(length=255), nullable=True),
        sa.Column("encrypted_api_key", sa.Text(), nullable=True),
        sa.Column("encrypted_api_secret", sa.Text(), nullable=True),
        sa.Column("encrypted_access_token", sa.Text(), nullable=True),
        sa.Column("api_key_last_four", sa.String(length=4), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "status",
            sa.Enum(
                "NOT_CONFIGURED",
                "UNTESTED",
                "CONNECTED",
                "ERROR",
                "DISABLED",
                name="providerstatus",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column("last_tested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_broker_connections_user_id", "broker_connections", ["user_id"])
    op.create_index("ix_broker_connections_provider", "broker_connections", ["provider"])
    op.create_index("ix_broker_connections_environment", "broker_connections", ["environment"])
    op.create_index("ix_broker_connections_created_at", "broker_connections", ["created_at"])
    op.create_index(
        "ix_broker_connections_user_env", "broker_connections", ["user_id", "environment"]
    )

    op.create_table(
        "auto_trading_policies",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("broker_account_id", sa.Uuid(), nullable=True),
        sa.Column(
            "environment",
            sa.Enum("DEMO", "LIVE", name="brokerenvironment", native_enum=False),
            nullable=False,
        ),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("allow_open", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("allow_add", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("allow_reduce", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("allow_close", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("allow_cancel", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("allow_replace", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("allow_manage_manual_positions", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("allow_manage_manual_orders", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("allowed_asset_classes", sa.JSON(), nullable=True),
        sa.Column("allowed_symbols", sa.JSON(), nullable=True),
        sa.Column("max_trade_notional", sa.Numeric(28, 10), nullable=True),
        sa.Column("max_position_notional", sa.Numeric(28, 10), nullable=True),
        sa.Column("max_trades_per_day", sa.Integer(), nullable=True),
        sa.Column("cooldown_seconds", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("min_agent_confidence", sa.Numeric(6, 4), nullable=True),
        sa.Column("require_strategy_signal", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("min_strategy_confidence", sa.Numeric(6, 4), nullable=True),
        sa.Column("notes", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["broker_account_id"], ["broker_accounts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_auto_trading_policies_user_id", "auto_trading_policies", ["user_id"])
    op.create_index(
        "ix_auto_trading_policies_broker_account_id", "auto_trading_policies", ["broker_account_id"]
    )
    op.create_index("ix_auto_trading_policies_created_at", "auto_trading_policies", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_auto_trading_policies_created_at", table_name="auto_trading_policies")
    op.drop_index("ix_auto_trading_policies_broker_account_id", table_name="auto_trading_policies")
    op.drop_index("ix_auto_trading_policies_user_id", table_name="auto_trading_policies")
    op.drop_table("auto_trading_policies")

    op.drop_index("ix_broker_connections_user_env", table_name="broker_connections")
    op.drop_index("ix_broker_connections_created_at", table_name="broker_connections")
    op.drop_index("ix_broker_connections_environment", table_name="broker_connections")
    op.drop_index("ix_broker_connections_provider", table_name="broker_connections")
    op.drop_index("ix_broker_connections_user_id", table_name="broker_connections")
    op.drop_table("broker_connections")

    with op.batch_alter_table("broker_accounts", schema=None) as batch:
        batch.drop_column("environment")
