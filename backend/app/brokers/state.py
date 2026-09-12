"""Order state machine.

Legal transitions live in exactly one place so endpoints and services cannot
scatter (or bypass) them. Terminal states have no outgoing transitions.
"""

from __future__ import annotations

from app.models.enums import OrderStatus

TERMINAL_STATES: frozenset[OrderStatus] = frozenset(
    {
        OrderStatus.FILLED,
        OrderStatus.CANCELLED,
        OrderStatus.REJECTED,
        OrderStatus.FAILED,
    }
)

ALLOWED_TRANSITIONS: dict[OrderStatus, frozenset[OrderStatus]] = {
    OrderStatus.CREATED: frozenset(
        {
            OrderStatus.VALIDATED,
            OrderStatus.SUBMITTED,
            OrderStatus.REJECTED,
            OrderStatus.FAILED,
            OrderStatus.CANCELLED,
        }
    ),
    OrderStatus.VALIDATED: frozenset(
        {
            OrderStatus.SUBMITTED,
            OrderStatus.REJECTED,
            OrderStatus.FAILED,
            OrderStatus.CANCELLED,
        }
    ),
    OrderStatus.SUBMITTED: frozenset(
        {
            OrderStatus.ACCEPTED,
            OrderStatus.PARTIALLY_FILLED,
            OrderStatus.FILLED,
            OrderStatus.REJECTED,
            OrderStatus.CANCELLED,
            OrderStatus.FAILED,
        }
    ),
    OrderStatus.ACCEPTED: frozenset(
        {
            OrderStatus.PARTIALLY_FILLED,
            OrderStatus.FILLED,
            OrderStatus.CANCELLED,
            OrderStatus.REJECTED,
            OrderStatus.FAILED,
        }
    ),
    OrderStatus.PARTIALLY_FILLED: frozenset(
        {
            OrderStatus.PARTIALLY_FILLED,
            OrderStatus.FILLED,
            OrderStatus.CANCELLED,
        }
    ),
    OrderStatus.FILLED: frozenset(),
    OrderStatus.CANCELLED: frozenset(),
    OrderStatus.REJECTED: frozenset(),
    OrderStatus.FAILED: frozenset(),
}

# States in which an order is still working and may receive further fills.
OPEN_STATES: frozenset[OrderStatus] = frozenset(
    {
        OrderStatus.CREATED,
        OrderStatus.VALIDATED,
        OrderStatus.SUBMITTED,
        OrderStatus.ACCEPTED,
        OrderStatus.PARTIALLY_FILLED,
    }
)

# States from which an order may be cancelled.
CANCELLABLE_STATES: frozenset[OrderStatus] = frozenset(
    {
        OrderStatus.CREATED,
        OrderStatus.VALIDATED,
        OrderStatus.SUBMITTED,
        OrderStatus.ACCEPTED,
        OrderStatus.PARTIALLY_FILLED,
    }
)


def is_terminal(status: OrderStatus) -> bool:
    return status in TERMINAL_STATES


def can_transition(current: OrderStatus, target: OrderStatus) -> bool:
    return target in ALLOWED_TRANSITIONS[current]


def assert_transition(current: OrderStatus, target: OrderStatus) -> None:
    from app.brokers.exceptions import InvalidOrderStateTransitionError

    if not can_transition(current, target):
        raise InvalidOrderStateTransitionError(
            f"Illegal order status transition {current.value} -> {target.value}",
            details={"from": current.value, "to": target.value},
        )
