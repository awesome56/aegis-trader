"""strategy signals phase 5 schema

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-09-13 15:00:00.000000

Adds the fields required to make strategy signals queryable and de-duplicated:
asset linkage, market regime, the data timestamp the signal was derived from, a
signal expiry, supporting indexes and a unique dedupe key.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c3d4e5f6a7b8"
down_revision: str | None = "b2c3d4e5f6a7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("strategy_signals") as batch:
        batch.add_column(sa.Column("asset_id", sa.Uuid(), nullable=True))
        batch.add_column(
            sa.Column(
                "market_regime",
                sa.Enum(
                    "BULLISH",
                    "BEARISH",
                    "SIDEWAYS",
                    "HIGH_VOLATILITY",
                    "LOW_VOLATILITY",
                    name="marketregime",
                    native_enum=False,
                ),
                nullable=True,
            )
        )
        batch.add_column(sa.Column("data_timestamp", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True))
        batch.create_index("ix_strategy_signals_asset_id", ["asset_id"])
        batch.create_index("ix_strategy_signals_data_timestamp", ["data_timestamp"])
        batch.create_index("ix_strategy_signals_expires_at", ["expires_at"])
        batch.create_index(
            "ix_strategy_signals_strategy_signal_time", ["strategy_id", "signal_time"]
        )
        batch.create_unique_constraint(
            "uq_strategy_signals_dedupe",
            ["strategy_id", "symbol", "timeframe", "direction", "data_timestamp"],
        )
        batch.create_foreign_key(
            "fk_strategy_signals_asset_id_assets",
            "assets",
            ["asset_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    with op.batch_alter_table("strategy_signals") as batch:
        batch.drop_constraint("fk_strategy_signals_asset_id_assets", type_="foreignkey")
        batch.drop_constraint("uq_strategy_signals_dedupe", type_="unique")
        batch.drop_index("ix_strategy_signals_strategy_signal_time")
        batch.drop_index("ix_strategy_signals_expires_at")
        batch.drop_index("ix_strategy_signals_data_timestamp")
        batch.drop_index("ix_strategy_signals_asset_id")
        batch.drop_column("expires_at")
        batch.drop_column("data_timestamp")
        batch.drop_column("market_regime")
        batch.drop_column("asset_id")
