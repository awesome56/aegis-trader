"""Risk-engine enumerations."""

from __future__ import annotations

from enum import StrEnum


class RuleSeverity(StrEnum):
    INFO = "INFO"  # informational; never rejects
    WARNING = "WARNING"  # a reducible constraint (size can be reduced)
    BLOCKING = "BLOCKING"  # hard rejection


class RiskStatus(StrEnum):
    SAFE = "SAFE"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"
