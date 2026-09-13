"""Agent-layer exceptions (safe, normalized)."""

from __future__ import annotations

from app.core.exceptions import AegisError


class AgentError(AegisError):
    code = "agent_error"
    status_code = 400


class AgentNotConfiguredError(AgentError):
    code = "agent_not_configured"
    status_code = 409


class AgentLoopLimitError(AgentError):
    code = "agent_loop_limit"


class AgentOutputError(AgentError):
    code = "agent_output_invalid"


class AgentRunConflictError(AgentError):
    code = "agent_run_conflict"
    status_code = 409
