"""backtesting phase 8: ownership, config snapshot, extended results

Revision ID: d4e5f6a7b8c9
Revises: cf0251ff393c
Create Date: 2026-09-13

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d4e5f6a7b8c9"
down_revision: str | None = "cf0251ff393c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("backtests", schema=None) as batch:
        batch.add_column(sa.Column("user_id", sa.Uuid(), nullable=True))
        batch.add_column(sa.Column("config_snapshot", sa.JSON(), nullable=True))
        batch.create_foreign_key(
            "fk_backtests_user_id_users", "users", ["user_id"], ["id"], ondelete="CASCADE"
        )
        batch.create_index("ix_backtests_user_id", ["user_id"])
        batch.create_index("ix_backtests_user_created", ["user_id", "created_at"])

    with op.batch_alter_table("backtest_results", schema=None) as batch:
        batch.add_column(sa.Column("metrics", sa.JSON(), nullable=True))
        batch.add_column(sa.Column("monthly_returns", sa.JSON(), nullable=True))
        batch.add_column(sa.Column("strategy_config", sa.JSON(), nullable=True))
        batch.add_column(sa.Column("engine_version", sa.String(length=32), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("backtest_results", schema=None) as batch:
        batch.drop_column("engine_version")
        batch.drop_column("strategy_config")
        batch.drop_column("monthly_returns")
        batch.drop_column("metrics")

    with op.batch_alter_table("backtests", schema=None) as batch:
        batch.drop_index("ix_backtests_user_created")
        batch.drop_index("ix_backtests_user_id")
        batch.drop_constraint("fk_backtests_user_id_users", type_="foreignkey")
        batch.drop_column("config_snapshot")
        batch.drop_column("user_id")
