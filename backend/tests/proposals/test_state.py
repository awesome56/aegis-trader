"""TradeProposal state-machine invariants."""

from __future__ import annotations

import pytest
from app.core.exceptions import ConflictError
from app.models.enums import ProposalStatus as S
from app.proposals.state import (
    ALLOWED,
    CANCELLABLE,
    EVALUATABLE,
    EXECUTABLE,
    TERMINAL,
    assert_transition,
    can_transition,
)


def test_happy_path_is_legal() -> None:
    path = [
        (S.DRAFT, S.PENDING_RISK),
        (S.PENDING_RISK, S.RISK_APPROVED),
        (S.RISK_APPROVED, S.READY_FOR_EXECUTION),
        (S.READY_FOR_EXECUTION, S.EXECUTING),
        (S.EXECUTING, S.EXECUTED),
    ]
    for current, target in path:
        assert can_transition(current, target)


def test_terminal_states_have_no_exits() -> None:
    for status in TERMINAL:
        assert ALLOWED[status] == frozenset()


def test_executing_cannot_be_cancelled() -> None:
    assert not can_transition(S.EXECUTING, S.CANCELLED)
    with pytest.raises(ConflictError):
        assert_transition(S.EXECUTING, S.CANCELLED)


def test_sets_are_consistent() -> None:
    assert S.EXECUTING not in CANCELLABLE
    assert S.EXECUTED not in EXECUTABLE
    assert S.RISK_APPROVED in EVALUATABLE
    assert S.PENDING_RISK in CANCELLABLE
