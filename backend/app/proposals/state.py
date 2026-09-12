"""TradeProposal state machine (single source of legal transitions)."""

from __future__ import annotations

from app.core.exceptions import ConflictError
from app.models.enums import ProposalStatus as S

TERMINAL = frozenset({S.EXECUTED, S.CANCELLED, S.EXPIRED, S.FAILED})

ALLOWED: dict[S, frozenset[S]] = {
    S.DRAFT: frozenset({S.PENDING, S.PENDING_RISK, S.CANCELLED, S.EXPIRED}),
    S.PENDING: frozenset({S.PENDING_RISK, S.CANCELLED, S.EXPIRED}),
    S.PENDING_RISK: frozenset(
        {S.RISK_APPROVED, S.RISK_REJECTED, S.EXPIRED, S.FAILED, S.CANCELLED}
    ),
    S.RISK_APPROVED: frozenset({S.READY_FOR_EXECUTION, S.EXECUTING, S.EXPIRED, S.CANCELLED}),
    S.APPROVED: frozenset({S.READY_FOR_EXECUTION, S.EXECUTING, S.EXPIRED, S.CANCELLED}),
    S.READY_FOR_EXECUTION: frozenset({S.EXECUTING, S.EXPIRED, S.CANCELLED}),
    S.EXECUTING: frozenset({S.EXECUTED, S.FAILED}),
    S.RISK_REJECTED: frozenset({S.CANCELLED}),
    S.REJECTED: frozenset({S.CANCELLED}),
    S.EXECUTED: frozenset(),
    S.CANCELLED: frozenset(),
    S.EXPIRED: frozenset(),
    S.FAILED: frozenset(),
}

CANCELLABLE = frozenset(
    {S.DRAFT, S.PENDING, S.PENDING_RISK, S.RISK_APPROVED, S.APPROVED, S.READY_FOR_EXECUTION}
)
EVALUATABLE = frozenset({S.DRAFT, S.PENDING, S.PENDING_RISK, S.RISK_APPROVED, S.APPROVED})
EXECUTABLE = frozenset({S.RISK_APPROVED, S.READY_FOR_EXECUTION, S.APPROVED})


def can_transition(current: S, target: S) -> bool:
    return target in ALLOWED[current]


def assert_transition(current: S, target: S) -> None:
    if not can_transition(current, target):
        raise ConflictError(
            f"Illegal proposal transition {current.value} -> {target.value}",
            details={"from": current.value, "to": target.value},
        )
