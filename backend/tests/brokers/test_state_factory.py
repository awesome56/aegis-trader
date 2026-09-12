"""Order state machine and broker provider factory tests."""

from __future__ import annotations

import pytest
from app.brokers.exceptions import BrokerConfigurationError, InvalidOrderStateTransitionError
from app.brokers.factory import resolve_broker_provider
from app.brokers.state import (
    CANCELLABLE_STATES,
    OPEN_STATES,
    assert_transition,
    can_transition,
    is_terminal,
)
from app.models.enums import OrderStatus

from .conftest import broker_settings


def test_legal_and_illegal_transitions() -> None:
    assert can_transition(OrderStatus.SUBMITTED, OrderStatus.FILLED)
    assert can_transition(OrderStatus.PARTIALLY_FILLED, OrderStatus.FILLED)
    assert not can_transition(OrderStatus.FILLED, OrderStatus.CANCELLED)
    assert not can_transition(OrderStatus.CANCELLED, OrderStatus.FILLED)
    assert not can_transition(OrderStatus.REJECTED, OrderStatus.SUBMITTED)
    with pytest.raises(InvalidOrderStateTransitionError):
        assert_transition(OrderStatus.FILLED, OrderStatus.CANCELLED)


def test_terminal_and_open_sets() -> None:
    assert is_terminal(OrderStatus.FILLED)
    assert is_terminal(OrderStatus.REJECTED)
    assert not is_terminal(OrderStatus.PARTIALLY_FILLED)
    assert OrderStatus.SUBMITTED in OPEN_STATES
    assert OrderStatus.PARTIALLY_FILLED in CANCELLABLE_STATES
    assert OrderStatus.FILLED not in CANCELLABLE_STATES


def test_factory_accepts_paper() -> None:
    assert resolve_broker_provider(broker_settings()) == "paper"


@pytest.mark.parametrize("provider", ["alpaca", "ibkr", "interactive_brokers", "live", "binance"])
def test_factory_rejects_live_providers_while_locked(provider: str) -> None:
    settings = broker_settings(BROKER_PROVIDER=provider)
    with pytest.raises(BrokerConfigurationError) as excinfo:
        resolve_broker_provider(settings)
    assert (
        "interlock" in str(excinfo.value).lower() or "not implemented" in str(excinfo.value).lower()
    )
