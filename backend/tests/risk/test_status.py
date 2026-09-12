"""Risk status / utilization tests."""

from __future__ import annotations

from decimal import Decimal

from app.risk.enums import RiskStatus
from app.risk.status import (
    status_from_results,
    status_from_utilization_rows,
    utilization,
    utilization_status,
)
from app.risk.types import RuleResult


def test_utilization_and_status() -> None:
    assert utilization(Decimal("50"), Decimal("100")) == Decimal("50")
    assert utilization(Decimal("0"), Decimal("0")) == Decimal("0")
    assert utilization(Decimal("1"), Decimal("0")) == Decimal("100")
    assert utilization_status(Decimal("10"), Decimal("80"), Decimal("100")) is RiskStatus.SAFE
    assert utilization_status(Decimal("90"), Decimal("80"), Decimal("100")) is RiskStatus.WARNING
    assert utilization_status(Decimal("100"), Decimal("80"), Decimal("100")) is RiskStatus.CRITICAL


def test_status_from_results() -> None:
    passing = [
        RuleResult(key="a", passed=True, severity="INFO", message="ok")  # type: ignore[arg-type]
    ]
    warning = [
        RuleResult(key="b", passed=False, severity="WARNING", message="reduce")  # type: ignore[arg-type]
    ]
    blocking = [
        RuleResult(key="c", passed=False, severity="BLOCKING", message="no")  # type: ignore[arg-type]
    ]
    assert status_from_results(passing) is RiskStatus.SAFE
    assert status_from_results(warning) is RiskStatus.WARNING
    assert status_from_results(blocking) is RiskStatus.CRITICAL


def test_status_from_utilization_rows() -> None:
    rows = [
        {"status": RiskStatus.SAFE},
        {"status": RiskStatus.WARNING},
    ]
    assert status_from_utilization_rows(rows) is RiskStatus.WARNING
    rows.append({"status": RiskStatus.CRITICAL})
    assert status_from_utilization_rows(rows) is RiskStatus.CRITICAL
