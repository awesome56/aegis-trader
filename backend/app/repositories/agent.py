"""Agent run/decision repositories."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import func, select

from app.models.agent import AgentDecision, AgentRun
from app.models.enums import RunStatus
from app.repositories.base import BaseRepository


class AgentRunRepository(BaseRepository[AgentRun]):
    model = AgentRun

    async def get_for_user(self, run_id: uuid.UUID, user_id: uuid.UUID) -> AgentRun | None:
        stmt = select(AgentRun).where(AgentRun.id == run_id, AgentRun.user_id == user_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_locked(self, run_id: uuid.UUID) -> AgentRun | None:
        stmt = select(AgentRun).where(AgentRun.id == run_id).with_for_update()
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_for_user(
        self, user_id: uuid.UUID, *, limit: int = 50, offset: int = 0
    ) -> list[AgentRun]:
        stmt = (
            select(AgentRun)
            .where(AgentRun.user_id == user_id)
            .order_by(AgentRun.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count_for_user(self, user_id: uuid.UUID) -> int:
        stmt = select(func.count()).select_from(AgentRun).where(AgentRun.user_id == user_id)
        return int(await self.session.scalar(stmt) or 0)

    async def count_active_for_user(self, user_id: uuid.UUID) -> int:
        stmt = (
            select(func.count())
            .select_from(AgentRun)
            .where(
                AgentRun.user_id == user_id,
                AgentRun.status.in_([RunStatus.PENDING, RunStatus.RUNNING]),
            )
        )
        return int(await self.session.scalar(stmt) or 0)

    async def count_since(self, user_id: uuid.UUID, since: datetime) -> int:
        stmt = (
            select(func.count())
            .select_from(AgentRun)
            .where(AgentRun.user_id == user_id, AgentRun.created_at >= since)
        )
        return int(await self.session.scalar(stmt) or 0)

    async def latest_for_user(self, user_id: uuid.UUID) -> AgentRun | None:
        stmt = (
            select(AgentRun)
            .where(AgentRun.user_id == user_id)
            .order_by(AgentRun.created_at.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def count_recent_failures(self, user_id: uuid.UUID, since: datetime) -> int:
        stmt = (
            select(func.count())
            .select_from(AgentRun)
            .where(
                AgentRun.user_id == user_id,
                AgentRun.status == RunStatus.FAILED,
                AgentRun.created_at >= since,
            )
        )
        return int(await self.session.scalar(stmt) or 0)


class AgentDecisionRepository(BaseRepository[AgentDecision]):
    model = AgentDecision

    async def get_for_user(
        self, decision_id: uuid.UUID, user_id: uuid.UUID
    ) -> AgentDecision | None:
        stmt = (
            select(AgentDecision)
            .join(AgentRun, AgentDecision.agent_run_id == AgentRun.id)
            .where(AgentDecision.id == decision_id, AgentRun.user_id == user_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_for_user(
        self, user_id: uuid.UUID, *, limit: int = 50, offset: int = 0
    ) -> list[AgentDecision]:
        stmt = (
            select(AgentDecision)
            .join(AgentRun, AgentDecision.agent_run_id == AgentRun.id)
            .where(AgentRun.user_id == user_id)
            .order_by(AgentDecision.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count_for_user(self, user_id: uuid.UUID) -> int:
        stmt = (
            select(func.count())
            .select_from(AgentDecision)
            .join(AgentRun, AgentDecision.agent_run_id == AgentRun.id)
            .where(AgentRun.user_id == user_id)
        )
        return int(await self.session.scalar(stmt) or 0)
