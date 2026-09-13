"""AI agent layer (Phase 9).

The agent may analyze and propose; it can never execute. This boundary is
enforced by the tool registry (no execution tools) and architecture tests.
"""

from app.agents.agent import AGENT_NAME, TradingAnalysisAgent
from app.agents.enums import AgentAction, AgentRunMode, EvidenceType
from app.agents.service import AgentService
from app.agents.tools import AgentToolContext, AgentToolRegistry
from app.agents.types import (
    AgentEvidence,
    AgentOutcome,
    ProposedTrade,
    ToolCallRecord,
    TradingAnalysisResult,
)

__all__ = [
    "AGENT_NAME",
    "AgentAction",
    "AgentEvidence",
    "AgentOutcome",
    "AgentRunMode",
    "AgentService",
    "AgentToolContext",
    "AgentToolRegistry",
    "EvidenceType",
    "ProposedTrade",
    "ToolCallRecord",
    "TradingAnalysisAgent",
    "TradingAnalysisResult",
]
