"""Risk rule contract."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.risk.enums import RuleSeverity
from app.risk.types import RiskContext, RuleResult


class RiskRule(ABC):
    key: str
    order: int = 100
    #: Severity applied when the rule fails (rules may downgrade to WARNING).
    failure_severity: RuleSeverity = RuleSeverity.BLOCKING

    @abstractmethod
    def evaluate(self, context: RiskContext) -> RuleResult:
        """Evaluate read-only state and return a typed result. No IO, no exceptions
        for ordinary rejections."""

    def _result(
        self,
        *,
        passed: bool,
        message: str,
        severity: RuleSeverity | None = None,
        current: object | None = None,
        limit: object | None = None,
        utilization_percent: object | None = None,
        metadata: dict | None = None,
    ) -> RuleResult:
        return RuleResult(
            key=self.key,
            passed=passed,
            severity=severity or self.failure_severity,
            message=message,
            current=current,
            limit=limit,
            utilization_percent=utilization_percent,
            metadata=metadata,
        )
