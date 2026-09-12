"""Strategy realtime event tests."""

from __future__ import annotations

from app.realtime.events import DomainEvent
from app.realtime.publisher import get_event_publisher, publish_pending, set_event_publisher

from tests.strategies.conftest import uptrend


class RecordingPublisher:
    def __init__(self) -> None:
        self.events: list[DomainEvent] = []

    async def publish(self, event: DomainEvent) -> None:
        self.events.append(event)


async def test_strategy_signal_event_published(strategy_env) -> None:  # noqa: ANN001
    recorder = RecordingPublisher()
    original = get_event_publisher()
    set_event_publisher(recorder)
    try:
        env = await strategy_env(uptrend())
        await env.service.evaluate("TEST", "1h")
        await publish_pending(env.session.info)
    finally:
        set_event_publisher(original)

    signal_events = [event for event in recorder.events if event.event == "strategy.signal"]
    assert len(signal_events) == 1
    payload = signal_events[0].data
    assert payload["symbol"] == "TEST"
    assert payload["direction"] == "LONG"
    assert payload["strategy"] == "trend_following"
    assert signal_events[0].event_id


async def test_enable_toggle_event(strategy_env) -> None:  # noqa: ANN001
    recorder = RecordingPublisher()
    original = get_event_publisher()
    set_event_publisher(recorder)
    try:
        env = await strategy_env(uptrend())
        strategy = (await env.service.list_strategies())[0]
        await env.service.set_enabled(strategy, False)
        await publish_pending(env.session.info)
    finally:
        set_event_publisher(original)

    assert any(event.event == "strategy.disabled" for event in recorder.events)
