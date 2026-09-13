"""AI provider configuration repository."""

from __future__ import annotations

import uuid

from sqlalchemy import func, select, update

from app.models.ai import AIProviderConfig
from app.repositories.base import BaseRepository


class AIProviderConfigRepository(BaseRepository[AIProviderConfig]):
    model = AIProviderConfig

    async def list_for_user(self, user_id: uuid.UUID) -> list[AIProviderConfig]:
        stmt = (
            select(AIProviderConfig)
            .where(AIProviderConfig.user_id == user_id)
            .order_by(AIProviderConfig.is_default.desc(), AIProviderConfig.created_at.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_for_user(
        self, config_id: uuid.UUID, user_id: uuid.UUID
    ) -> AIProviderConfig | None:
        stmt = select(AIProviderConfig).where(
            AIProviderConfig.id == config_id, AIProviderConfig.user_id == user_id
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_default_for_user(self, user_id: uuid.UUID) -> AIProviderConfig | None:
        stmt = (
            select(AIProviderConfig)
            .where(AIProviderConfig.user_id == user_id, AIProviderConfig.is_default.is_(True))
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def count_for_user(self, user_id: uuid.UUID) -> int:
        stmt = (
            select(func.count())
            .select_from(AIProviderConfig)
            .where(AIProviderConfig.user_id == user_id)
        )
        return int(await self.session.scalar(stmt) or 0)

    async def clear_defaults(self, user_id: uuid.UUID) -> None:
        await self.session.execute(
            update(AIProviderConfig)
            .where(AIProviderConfig.user_id == user_id, AIProviderConfig.is_default.is_(True))
            .values(is_default=False)
            .execution_options(synchronize_session=False)
        )
