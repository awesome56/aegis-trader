"""phase 9: encrypted AI provider configurations

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-09-13

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e5f6a7b8c9d0"
down_revision: str | None = "d4e5f6a7b8c9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ai_provider_configs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("model", sa.String(length=128), nullable=False),
        sa.Column("base_url", sa.String(length=255), nullable=True),
        sa.Column("encrypted_api_key", sa.Text(), nullable=True),
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
    op.create_index("ix_ai_provider_configs_user_id", "ai_provider_configs", ["user_id"])
    op.create_index("ix_ai_provider_configs_provider", "ai_provider_configs", ["provider"])
    op.create_index("ix_ai_provider_configs_created_at", "ai_provider_configs", ["created_at"])
    op.create_index(
        "ix_ai_provider_configs_user_default", "ai_provider_configs", ["user_id", "is_default"]
    )


def downgrade() -> None:
    op.drop_index("ix_ai_provider_configs_user_default", table_name="ai_provider_configs")
    op.drop_index("ix_ai_provider_configs_created_at", table_name="ai_provider_configs")
    op.drop_index("ix_ai_provider_configs_provider", table_name="ai_provider_configs")
    op.drop_index("ix_ai_provider_configs_user_id", table_name="ai_provider_configs")
    op.drop_table("ai_provider_configs")
