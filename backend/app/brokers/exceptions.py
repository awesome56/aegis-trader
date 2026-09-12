"""Normalised broker exceptions.

Provider-specific failures must be translated into these before leaving an
adapter. They extend ``AegisError`` so the API layer maps them to consistent
HTTP responses automatically.
"""

from __future__ import annotations

from app.core.exceptions import AegisError


class BrokerError(AegisError):
    status_code = 502
    code = "broker_error"


class BrokerConfigurationError(AegisError):
    """Invalid or unsafe broker configuration (e.g. live provider while locked)."""

    status_code = 500
    code = "broker_configuration_error"


class BrokerUnavailableError(BrokerError):
    status_code = 503
    code = "broker_unavailable"


class BrokerAuthenticationError(BrokerError):
    status_code = 502
    code = "broker_authentication_error"


class BrokerRejectedOrderError(BrokerError):
    status_code = 422
    code = "broker_rejected_order"


class InsufficientFundsError(BrokerRejectedOrderError):
    code = "insufficient_funds"


class InsufficientPositionError(BrokerRejectedOrderError):
    code = "insufficient_position"


class UnsupportedOrderTypeError(BrokerRejectedOrderError):
    code = "unsupported_order_type"


class UnsupportedTimeInForceError(BrokerRejectedOrderError):
    code = "unsupported_time_in_force"


class InvalidOrderError(BrokerRejectedOrderError):
    code = "invalid_order"


class OrderNotFoundError(BrokerError):
    status_code = 404
    code = "order_not_found"


class OrderNotCancellableError(BrokerError):
    status_code = 409
    code = "order_not_cancellable"


class DuplicateOrderError(BrokerError):
    status_code = 409
    code = "duplicate_order"


class InvalidOrderStateTransitionError(BrokerError):
    status_code = 409
    code = "invalid_order_state_transition"
