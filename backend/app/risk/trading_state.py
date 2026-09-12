"""Persisted system-wide trading state (kill switch)."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.models.enums import TradingState
from app.models.system import SystemState
from app.realtime.events import DomainEvent, queue_event
from app.repositories.risk import SystemStateRepository

logger = get_logger(__name__)

STATE_EVENTS: dict[TradingState, str] = {
    TradingState.TRADING_ENABLED: "system.trading_resumed",
    TradingState.TRADING_PAUSED: "system.trading_paused",
    TradingState.TRADING_DISABLED: "system.trading_disabled",
    TradingState.EMERGENCY_STOP: "system.emergency_stop",
}


class TradingStateService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        settings: Settings | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._session = session
        self._settings = settings or get_settings()
        self._clock = clock or (lambda: datetime.now(UTC))
        self._repo = SystemStateRepository(session)

    async def get_or_create(self, key: str = "trading") -> SystemState:
        existing = await self._repo.get_by_key(key)
        if existing is not None:
            return existing
        now = self._clock()
        default_state = TradingState(self._settings.RISK_DEFAULT_TRADING_STATE)
        row = SystemState(
            key=key,
            trading_state=default_state,
            previous_state=None,
            reason="initialised",
            actor="system",
            changed_at=now,
            created_at=now,
            updated_at=now,
        )
        return await self._repo.add(row)

    async def transition(
        self, new_state: TradingState, *, reason: str, actor: str | None
    ) -> SystemState:
        row = await self.get_or_create()
        previous = row.trading_state
        now = self._clock()
        row.previous_state = previous
        row.trading_state = new_state
        row.reason = reason
        row.actor = actor
        row.changed_at = now
        row.updated_at = now
        await self._session.flush()

        queue_event(
            self._session.info,
            DomainEvent(
                event=STATE_EVENTS[new_state],
                data={
                    "previous_state": previous.value,
                    "trading_state": new_state.value,
                    "reason": reason,
                    "actor": actor,
                },
            ),
        )
        logger.warning(
            "trading_state_changed",
            previous=previous.value,
            new=new_state.value,
            actor=actor,
        )
        return row

    def state_payload(self, row: SystemState) -> dict[str, Any]:
        return {
            "trading_state": row.trading_state.value,
            "previous_state": row.previous_state.value if row.previous_state else None,
            "reason": row.reason,
            "actor": row.actor,
            "changed_at": row.changed_at.isoformat() if row.changed_at else None,
        }
