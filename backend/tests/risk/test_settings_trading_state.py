"""Risk settings and persisted trading-state tests."""

from __future__ import annotations

import uuid
from decimal import Decimal

from app.models.enums import TradingState
from app.models.system import SystemState
from app.models.user import User
from app.realtime.events import DomainEvent
from app.realtime.publisher import get_event_publisher, publish_pending, set_event_publisher
from app.risk.settings_service import RiskSettingsService
from app.risk.trading_state import TradingStateService
from sqlalchemy import func, select

from tests.strategies.conftest import strategy_settings


async def _user(db_session) -> User:  # noqa: ANN001
    user = User(email=f"rs-{uuid.uuid4().hex[:8]}@example.com", hashed_password="x", is_active=True)
    db_session.add(user)
    await db_session.flush()
    return user


class _Recorder:
    def __init__(self) -> None:
        self.events: list[DomainEvent] = []

    async def publish(self, event: DomainEvent) -> None:
        self.events.append(event)


async def test_settings_seeded_from_environment(db_session) -> None:  # noqa: ANN001
    settings = strategy_settings()
    service = RiskSettingsService(db_session, settings)
    row = await service.get_or_create((await _user(db_session)).id)
    snapshot = service.to_snapshot(row)
    assert snapshot.max_position_percent == Decimal(str(settings.MAX_POSITION_PERCENTAGE))
    assert snapshot.max_open_positions == settings.MAX_OPEN_POSITIONS

    again = await service.get_or_create(row.user_id)
    assert again.id == row.id
    from app.repositories.risk import RiskSettingsRepository

    count = await RiskSettingsRepository(db_session).count(user_id=row.user_id)
    assert count == 1


async def test_settings_update(db_session) -> None:  # noqa: ANN001
    service = RiskSettingsService(db_session, strategy_settings())
    row = await service.get_or_create((await _user(db_session)).id)
    await service.update(row, {"max_position_percent": 8, "require_stop_loss": False})
    snapshot = service.to_snapshot(row)
    assert snapshot.max_position_percent == 8
    assert snapshot.require_stop_loss is False


async def test_trading_state_default_and_transitions(db_session) -> None:  # noqa: ANN001
    service = TradingStateService(db_session, settings=strategy_settings())
    row = await service.get_or_create()
    assert row.trading_state is TradingState.TRADING_ENABLED

    await service.transition(TradingState.TRADING_PAUSED, reason="test", actor="tester")
    # A brand-new service instance sees the persisted state (restart-safe).
    fresh = TradingStateService(db_session, settings=strategy_settings())
    reloaded = await fresh.get_or_create()
    assert reloaded.trading_state is TradingState.TRADING_PAUSED
    assert reloaded.previous_state is TradingState.TRADING_ENABLED
    assert reloaded.reason == "test"


async def test_transition_emits_event(db_session) -> None:  # noqa: ANN001
    recorder = _Recorder()
    original = get_event_publisher()
    set_event_publisher(recorder)
    try:
        service = TradingStateService(db_session, settings=strategy_settings())
        await service.transition(TradingState.EMERGENCY_STOP, reason="test", actor="tester")
        await publish_pending(db_session.info)
    finally:
        set_event_publisher(original)
    names = [event.event for event in recorder.events]
    assert "system.emergency_stop" in names


async def test_emergency_stop_persists(db_session) -> None:  # noqa: ANN001
    service = TradingStateService(db_session, settings=strategy_settings())
    await service.transition(TradingState.EMERGENCY_STOP, reason="x", actor="t")
    rows = await db_session.scalar(select(func.count()).select_from(SystemState))
    assert rows == 1
