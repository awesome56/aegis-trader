"""Provider-agnostic LLM request/response types.

Normalized so provider-specific raw payloads never spread through agent code.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

Role = Literal["system", "user", "assistant", "tool"]


class LLMMessage(BaseModel):
    model_config = ConfigDict(frozen=True)

    role: Role
    content: str
    name: str | None = None
    tool_call_id: str | None = None


class LLMToolSpec(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    description: str
    parameters: dict[str, Any]


class LLMToolCall(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class LLMUsage(BaseModel):
    model_config = ConfigDict(frozen=True)

    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    estimated_cost: Decimal | None = None


class LLMRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    system_prompt: str | None = None
    messages: list[LLMMessage] = Field(default_factory=list)
    tools: list[LLMToolSpec] = Field(default_factory=list)
    temperature: float = 0.0
    max_tokens: int | None = None
    response_schema: dict[str, Any] | None = None


class LLMResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    content: str = ""
    tool_calls: list[LLMToolCall] = Field(default_factory=list)
    usage: LLMUsage = Field(default_factory=LLMUsage)
    provider: str
    model: str
    request_id: str | None = None
    finish_reason: str | None = None
    latency_ms: int = 0


class LLMModel(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    label: str | None = None


class ProviderTestResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    ok: bool
    status: str
    detail: str | None = None
    models: list[LLMModel] = Field(default_factory=list)
