"""phase 9b: agent run/decision fields for TradingAnalysisAgent

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-09-13

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f6a7b8c9d0e1"
down_revision: str | None = "e5f6a7b8c9d0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("agent_runs", schema=None) as batch:
        batch.add_column(sa.Column("user_id", sa.Uuid(), nullable=True))
        batch.add_column(sa.Column("provider_config_id", sa.Uuid(), nullable=True))
        batch.add_column(sa.Column("provider", sa.String(length=32), nullable=True))
        batch.add_column(
            sa.Column(
                "mode",
                sa.Enum("ANALYSIS_ONLY", "PROPOSE", name="agentmode", native_enum=False),
                nullable=False,
                server_default="ANALYSIS_ONLY",
            )
        )
        batch.add_column(sa.Column("prompt", sa.Text(), nullable=True))
        batch.add_column(sa.Column("usage", sa.JSON(), nullable=True))
        batch.add_column(sa.Column("latency_ms", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("proposal_id", sa.Uuid(), nullable=True))
        batch.create_foreign_key(
            "fk_agent_runs_user_id_users", "users", ["user_id"], ["id"], ondelete="CASCADE"
        )
        batch.create_foreign_key(
            "fk_agent_runs_provider_config_id",
            "ai_provider_configs",
            ["provider_config_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch.create_foreign_key(
            "fk_agent_runs_proposal_id",
            "trade_proposals",
            ["proposal_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch.create_index("ix_agent_runs_user_id", ["user_id"])
        batch.create_index("ix_agent_runs_user_created", ["user_id", "created_at"])
        batch.create_index("ix_agent_runs_status_created", ["status", "created_at"])
        batch.create_index("ix_agent_runs_proposal_id", ["proposal_id"])

    with op.batch_alter_table("agent_decisions", schema=None) as batch:
        batch.add_column(sa.Column("concerns", sa.JSON(), nullable=True))
        batch.add_column(
            sa.Column(
                "proposal_recommended",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("agent_decisions", schema=None) as batch:
        batch.drop_column("proposal_recommended")
        batch.drop_column("concerns")

    with op.batch_alter_table("agent_runs", schema=None) as batch:
        batch.drop_index("ix_agent_runs_proposal_id")
        batch.drop_index("ix_agent_runs_status_created")
        batch.drop_index("ix_agent_runs_user_created")
        batch.drop_index("ix_agent_runs_user_id")
        batch.drop_constraint("fk_agent_runs_proposal_id", type_="foreignkey")
        batch.drop_constraint("fk_agent_runs_provider_config_id", type_="foreignkey")
        batch.drop_constraint("fk_agent_runs_user_id_users", type_="foreignkey")
        batch.drop_column("proposal_id")
        batch.drop_column("latency_ms")
        batch.drop_column("usage")
        batch.drop_column("prompt")
        batch.drop_column("mode")
        batch.drop_column("provider")
        batch.drop_column("provider_config_id")
        batch.drop_column("user_id")
