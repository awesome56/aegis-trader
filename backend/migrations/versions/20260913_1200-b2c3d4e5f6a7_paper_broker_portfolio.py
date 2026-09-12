"""paper broker + portfolio phase 3/4 schema

Revision ID: b2c3d4e5f6a7
Revises: 9f1c2b7a4d10
Create Date: 2026-09-13 12:00:00.000000

Adds the columns required by the simulated broker and portfolio layers:
- order side becomes TradeSide (BUY/SELL) and gains time_in_force
- executions record gross/net amounts
- broker accounts track realized P&L and currency
- positions track cost basis
- portfolio snapshots gain market value, position count and interval uniqueness
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b2c3d4e5f6a7"
down_revision: str | None = "9f1c2b7a4d10"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("broker_accounts") as batch:
        batch.add_column(
            sa.Column("realized_pnl", sa.Numeric(precision=28, scale=10), nullable=False, server_default="0")
        )
        batch.add_column(
            sa.Column("currency", sa.String(length=8), nullable=False, server_default="USD")
        )

    with op.batch_alter_table("positions") as batch:
        batch.add_column(
            sa.Column("cost_basis", sa.Numeric(precision=28, scale=10), nullable=False, server_default="0")
        )

    with op.batch_alter_table("executions") as batch:
        batch.add_column(sa.Column("gross_amount", sa.Numeric(precision=28, scale=10), nullable=True))
        batch.add_column(sa.Column("net_amount", sa.Numeric(precision=28, scale=10), nullable=True))

    with op.batch_alter_table("orders") as batch:
        batch.add_column(sa.Column("asset_id", sa.Uuid(), nullable=True))
        batch.create_index("ix_orders_asset_id", ["asset_id"])
        batch.create_foreign_key(
            "fk_orders_asset_id_assets", "assets", ["asset_id"], ["id"], ondelete="SET NULL"
        )
        batch.alter_column(
            "side",
            existing_type=sa.Enum("LONG", "SHORT", name="positionside", native_enum=False),
            type_=sa.Enum("BUY", "SELL", name="tradeside", native_enum=False),
            existing_nullable=False,
        )
        batch.add_column(
            sa.Column(
                "time_in_force",
                sa.Enum("DAY", "GTC", name="timeinforce", native_enum=False),
                nullable=False,
                server_default="DAY",
            )
        )

    # Idempotency becomes per-account: replace the global unique index with a
    # non-unique index plus a composite unique constraint.
    with op.batch_alter_table("orders") as batch:
        batch.drop_index("ix_orders_idempotency_key")
    with op.batch_alter_table("orders") as batch:
        batch.create_index("ix_orders_idempotency_key", ["idempotency_key"], unique=False)
        batch.create_unique_constraint(
            "uq_orders_account_idempotency", ["broker_account_id", "idempotency_key"]
        )

    with op.batch_alter_table("portfolio_snapshots") as batch:
        batch.add_column(
            sa.Column("market_value", sa.Numeric(precision=28, scale=10), nullable=False, server_default="0")
        )
        batch.add_column(
            sa.Column("position_count", sa.Integer(), nullable=False, server_default="0")
        )
        batch.create_unique_constraint(
            "uq_portfolio_snapshots_portfolio_time", ["portfolio_id", "snapshot_time"]
        )


def downgrade() -> None:
    with op.batch_alter_table("portfolio_snapshots") as batch:
        batch.drop_constraint("uq_portfolio_snapshots_portfolio_time", type_="unique")
        batch.drop_column("position_count")
        batch.drop_column("market_value")

    with op.batch_alter_table("orders") as batch:
        batch.drop_constraint("uq_orders_account_idempotency", type_="unique")
        batch.drop_index("ix_orders_idempotency_key")
    with op.batch_alter_table("orders") as batch:
        batch.create_index("ix_orders_idempotency_key", ["idempotency_key"], unique=True)
        batch.drop_column("time_in_force")
        batch.drop_constraint("fk_orders_asset_id_assets", type_="foreignkey")
        batch.drop_index("ix_orders_asset_id")
        batch.drop_column("asset_id")
        batch.alter_column(
            "side",
            existing_type=sa.Enum("BUY", "SELL", name="tradeside", native_enum=False),
            type_=sa.Enum("LONG", "SHORT", name="positionside", native_enum=False),
            existing_nullable=False,
        )

    with op.batch_alter_table("executions") as batch:
        batch.drop_column("net_amount")
        batch.drop_column("gross_amount")

    with op.batch_alter_table("positions") as batch:
        batch.drop_column("cost_basis")

    with op.batch_alter_table("broker_accounts") as batch:
        batch.drop_column("currency")
        batch.drop_column("realized_pnl")
