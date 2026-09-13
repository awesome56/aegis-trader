"""TradingAnalysisAgent.

One agent only. It can read market/strategy/portfolio/risk context and create at
most one DRAFT TradeProposal. It has no execution capability by construction:
the tool registry exposes no execution tools and the agent never imports
broker/order/OrderManager code.
"""

from __future__ import annotations

import json
import time
import uuid
from decimal import Decimal

from app.agents.enums import AgentRunMode
from app.agents.exceptions import AgentLoopLimitError, AgentOutputError
from app.agents.prompts import SYSTEM_PROMPT, build_user_prompt
from app.agents.tools import AgentToolContext, AgentToolRegistry
from app.agents.types import AgentOutcome, ToolCallRecord, TradingAnalysisResult
from app.ai.base import LLMProvider
from app.ai.exceptions import LLMProviderError
from app.ai.types import LLMMessage, LLMRequest, LLMUsage
from app.core.config import Settings, get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

AGENT_NAME = "trading_analysis"


class TradingAnalysisAgent:
    name = AGENT_NAME

    def __init__(self, provider: LLMProvider, settings: Settings | None = None) -> None:
        self._provider = provider
        self._settings = settings or get_settings()

    async def run(
        self,
        *,
        context: AgentToolContext,
        run_key: str,
        question: str | None = None,
    ) -> AgentOutcome:
        registry = AgentToolRegistry(context)
        tool_specs = registry.specs()
        messages = [
            LLMMessage(
                role="user",
                content=build_user_prompt(
                    symbol=context.symbol,
                    timeframe=context.timeframe,
                    mode=context.mode,
                    question=question,
                ),
            )
        ]

        usage = LLMUsage()
        tool_records: list[ToolCallRecord] = []
        proposal_id: uuid.UUID | None = None
        started = time.perf_counter()
        max_iterations = self._settings.AGENT_MAX_TOOL_ITERATIONS

        for iteration in range(1, max_iterations + 1):
            request = LLMRequest(
                system_prompt=SYSTEM_PROMPT,
                messages=messages,
                tools=tool_specs,
                temperature=self._settings.AGENT_TEMPERATURE,
                max_tokens=self._settings.AGENT_MAX_OUTPUT_TOKENS,
            )
            response = await self._provider.generate(request)
            usage = _add_usage(usage, response.usage)

            if not response.tool_calls:
                result = _parse_result(response.content, context.symbol, context.mode)
                return AgentOutcome(
                    result=result,
                    tool_calls=tool_records,
                    usage=usage,
                    provider=response.provider,
                    model=response.model,
                    latency_ms=int((time.perf_counter() - started) * 1000),
                    iterations=iteration,
                    proposal_id=proposal_id,
                )

            for call in response.tool_calls:
                # Idempotency tied to the run + provider tool-call id.
                idempotency_key = f"{run_key}:{call.id or call.name}"
                ok, payload, summary = await registry.execute(
                    call.name, call.arguments, idempotency_key=idempotency_key
                )
                if call.name == "create_trade_proposal" and ok:
                    proposal_id = uuid.UUID(payload["proposal_id"])
                tool_records.append(ToolCallRecord(name=call.name, ok=ok, summary=summary))
                logger.info(
                    "agent_tool_called",
                    agent=self.name,
                    tool=call.name,
                    ok=ok,
                )
                messages.append(
                    LLMMessage(
                        role="user",
                        content=f"TOOL {call.name} result: {json.dumps(payload)[:4000]}",
                    )
                )

        raise AgentLoopLimitError(
            f"agent exceeded the maximum of {max_iterations} tool iterations"
        )


def _parse_result(content: str, symbol: str, mode: AgentRunMode) -> TradingAnalysisResult:
    raw = (content or "").strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        if "\n" in raw:
            raw = raw.split("\n", 1)[1]
    start = raw.find("{")
    end = raw.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise AgentOutputError("model did not return a structured JSON result")
    try:
        data = json.loads(raw[start : end + 1])
    except json.JSONDecodeError as exc:
        raise AgentOutputError("model returned invalid JSON") from exc
    data.setdefault("symbol", symbol)
    try:
        result = TradingAnalysisResult.model_validate(data)
    except Exception as exc:  # noqa: BLE001 - normalize validation failure
        raise AgentOutputError("model output failed schema validation") from exc

    # Enforce mode semantics regardless of what the model returned.
    if mode is AgentRunMode.ANALYSIS_ONLY and (
        result.proposal_recommended or result.proposed_trade is not None
    ):
        result = result.model_copy(
            update={"proposal_recommended": False, "proposed_trade": None}
        )
    return result


def _add_usage(total: LLMUsage, extra: LLMUsage) -> LLMUsage:
    return LLMUsage(
        input_tokens=total.input_tokens + extra.input_tokens,
        output_tokens=total.output_tokens + extra.output_tokens,
        total_tokens=total.total_tokens + extra.total_tokens,
        estimated_cost=(
            (total.estimated_cost or Decimal("0")) + (extra.estimated_cost or Decimal("0"))
        )
        if (total.estimated_cost is not None or extra.estimated_cost is not None)
        else None,
    )


__all__ = ["AGENT_NAME", "TradingAnalysisAgent", "LLMProviderError"]
