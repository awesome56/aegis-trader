"""market data phase 2: extend market_quotes and market_candles

Revision ID: 9f1c2b7a4d10
Revises: 32eb1398b34b
Create Date: 2026-09-13 09:00:00.000000

Adds the fields required by the provider-independent market-data layer:
quotes gain asset linkage and full OHLC/previous-close/currency context;
candles gain asset linkage, close time, trade count and VWAP. Candle uniqueness
remains (symbol, timeframe, candle_time) so providers cannot duplicate rows.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "9f1c2b7a4d10"
down_revision: str | None = "32eb1398b34b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("market_quotes") as batch:
        batch.add_column(sa.Column("asset_id", sa.Uuid(), nullable=True))
        batch.add_column(sa.Column("open", sa.Numeric(precision=28, scale=10), nullable=True))
        batch.add_column(sa.Column("high", sa.Numeric(precision=28, scale=10), nullable=True))
        batch.add_column(sa.Column("low", sa.Numeric(precision=28, scale=10), nullable=True))
        batch.add_column(
            sa.Column("previous_close", sa.Numeric(precision=28, scale=10), nullable=True)
        )
        batch.add_column(
            sa.Column("currency", sa.String(length=8), nullable=False, server_default="USD")
        )
        batch.create_index("ix_market_quotes_asset_id", ["asset_id"])
        batch.create_foreign_key(
            "fk_market_quotes_asset_id_assets",
            "assets",
            ["asset_id"],
            ["id"],
            ondelete="SET NULL",
        )

    with op.batch_alter_table("market_candles") as batch:
        batch.add_column(sa.Column("asset_id", sa.Uuid(), nullable=True))
        batch.add_column(sa.Column("trade_count", sa.BigInteger(), nullable=True))
        batch.add_column(sa.Column("vwap", sa.Numeric(precision=28, scale=10), nullable=True))
        batch.add_column(sa.Column("close_time", sa.DateTime(timezone=True), nullable=True))
        batch.create_index("ix_market_candles_asset_id", ["asset_id"])
        batch.create_foreign_key(
            "fk_market_candles_asset_id_assets",
            "assets",
            ["asset_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    with op.batch_alter_table("market_candles") as batch:
        batch.drop_constraint("fk_market_candles_asset_id_assets", type_="foreignkey")
        batch.drop_index("ix_market_candles_asset_id")
        batch.drop_column("close_time")
        batch.drop_column("vwap")
        batch.drop_column("trade_count")
        batch.drop_column("asset_id")

    with op.batch_alter_table("market_quotes") as batch:
        batch.drop_constraint("fk_market_quotes_asset_id_assets", type_="foreignkey")
        batch.drop_index("ix_market_quotes_asset_id")
        batch.drop_column("currency")
        batch.drop_column("previous_close")
        batch.drop_column("low")
        batch.drop_column("high")
        batch.drop_column("open")
        batch.drop_column("asset_id")
