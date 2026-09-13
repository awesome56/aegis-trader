"""TradingAnalysisAgent orchestration + persistence.

Agent runs never execute trades: they may only produce an analysis decision and
(optionally) a DRAFT TradeProposal sourced as AGENT.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.agent import AGENT_NAME, TradingAnalysisAgent
from app.agents.enums import AgentAction
from app.agents.exceptions import (
    AgentError,
    AgentNotConfiguredError,
    AgentRunConflictError,
)
from app.agents.tools import AgentToolContext
from app.agents.types import TradingAnalysisResult
from app.ai.factory import create_provider
from app.ai.security import CredentialError
from app.ai.service import AIProviderService
from app.core.config import Settings, get_settings
from app.core.exceptions import NotFoundError
from app.core.logging import get_logger
from app.models.agent import AgentDecision, AgentRun
from app.models.enums import (
    AgentMode,
    MarketRegime,
    NotificationSeverity,
    OrderAction,
    RunStatus,
)
from app.models.user import User
from app.notifications.service import CATEGORY_SYSTEM, CATEGORY_TRADING, NotificationService
from app.realtime.events import DomainEvent, queue_event
from app.repositories.agent import AgentDecisionRepository, AgentRunRepository

logger = get_logger(__name__)

_ACTION_MAP: dict[AgentAction, OrderAction] = {
    AgentAction.BUY: OrderAction.BUY,
    AgentAction.SELL: OrderAction.SELL,
    AgentAction.HOLD: OrderAction.HOLD,
    AgentAction.NO_ACTION: OrderAction.HOLD,
}


class AgentService:
    def __init__(self, session: AsyncSession, settings: Settings | None = None) -> None:
        self._session = session
        self._settings = settings or get_settings()
        self._runs = AgentRunRepository(session)
        self._decisions = AgentDecisionRepository(session)
        self._providers = AIProviderService(session, self._settings)

    # --- status -------------------------------------------------------------
    async def status(self, user_id: uuid.UUID) -> dict:
        config = await self._providers.resolve(user_id)
        last_run = await self._runs.latest_for_user(user_id)
        now = datetime.now(UTC)
        return {
            "enabled": self._settings.AGENT_ENABLED,
            "default_mode": self._settings.AGENT_DEFAULT_MODE,
            "provider": config.provider if config else None,
            "model": config.model if config else None,
            "provider_status": config.status.value if config else "NOT_CONFIGURED",
            "provider_config_id": str(config.id) if config else None,
            "running": await self._runs.count_active_for_user(user_id),
            "runs_today": await self._runs.count_since(user_id, now - timedelta(days=1)),
            "recent_failures": await self._runs.count_recent_failures(
                user_id, now - timedelta(days=1)
            ),
            "last_run": _run_summary(last_run) if last_run else None,
        }

    # --- creation -----------------------------------------------------------
    async def create_run(
        self,
        *,
        user_id: uuid.UUID,
        symbol: str,
        timeframe: str,
        mode: AgentMode,
        provider_config_id: uuid.UUID | None = None,
        question: str | None = None,
    ) -> AgentRun:
        if not self._settings.AGENT_ENABLED:
            raise AgentNotConfiguredError("the agent is disabled")
        if mode is AgentMode.PROPOSE and not self._settings.AI_ENABLED:
            raise AgentNotConfiguredError("AI features are disabled")

        if await self._runs.count_active_for_user(user_id) >= (
            self._settings.AGENT_MAX_CONCURRENT_RUNS_PER_USER
        ):
            raise AgentRunConflictError("too many running agent runs")
        if await self._runs.count_since(user_id, datetime.now(UTC) - timedelta(minutes=1)) >= (
            self._settings.AGENT_MAX_RUNS_PER_MINUTE
        ):
            raise AgentRunConflictError("agent run rate limit exceeded")

        config = await self._providers.resolve(user_id, provider_config_id)
        if config is None:
            raise AgentNotConfiguredError("no LLM provider is configured")

        now = datetime.now(UTC)
        run = AgentRun(
            user_id=user_id,
            provider_config_id=config.id if config.id else None,
            agent_name=AGENT_NAME,
            status=RunStatus.PENDING,
            provider=config.provider,
            model=config.model,
            mode=mode,
            prompt=question[: self._settings.AGENT_MAX_PROMPT_CHARS] if question else None,
            symbols=[symbol.strip().upper()],
            context={"timeframe": timeframe, "question": question},
            created_at=now,
            updated_at=now,
        )
        await self._runs.add(run)
        self._emit("agent.run_created", run)
        return run

    # --- execution ----------------------------------------------------------
    async def execute(self, run_id: uuid.UUID) -> AgentRun:
        run = await self._runs.get_locked(run_id)
        if run is None:
            raise NotFoundError(f"Agent run {run_id} not found")
        if run.status is RunStatus.COMPLETED:
            return run
        if run.status is RunStatus.CANCELLED:
            return run

        user = await self._session.get(User, run.user_id) if run.user_id else None
        if user is None:
            raise NotFoundError("agent run has no owner")

        now = datetime.now(UTC)
        run.status = RunStatus.RUNNING
        run.started_at = now
        run.updated_at = now
        run.error = None
        await self._session.flush()
        self._emit("agent.started", run)

        try:
            provider = await self._build_provider(run, user)
            symbol = (run.symbols or [user.email])[0]
            timeframe = str((run.context or {}).get("timeframe") or "1h")
            context = AgentToolContext(
                session=self._session,
                user=user,
                symbol=symbol,
                timeframe=timeframe,
                mode=AgentMode(run.mode),
                settings=self._settings,
            )
            agent = TradingAnalysisAgent(provider, self._settings)
            outcome = await asyncio.wait_for(
                agent.run(
                    context=context,
                    run_key=str(run.id),
                    question=run.prompt,
                ),
                timeout=self._settings.AGENT_RUN_TIMEOUT_SECONDS,
            )
            await self._persist_decision(run, outcome.result, outcome)
            run.status = RunStatus.COMPLETED
            run.completed_at = datetime.now(UTC)
            run.updated_at = run.completed_at
            run.latency_ms = outcome.latency_ms
            run.tokens_used = outcome.usage.total_tokens
            run.usage = outcome.usage.model_dump(mode="json")
            run.proposal_id = outcome.proposal_id
            await self._session.flush()
            self._emit("agent.completed", run, extra={"tool_calls": len(outcome.tool_calls)})
            if outcome.proposal_id is not None:
                self._emit(
                    "agent.proposal_created",
                    run,
                    extra={"proposal_id": str(outcome.proposal_id)},
                )
                await self._notify(
                    user.id,
                    "Agent created a proposal",
                    f"Agent proposed a {outcome.result.action.value} on {outcome.result.symbol}.",
                    NotificationSeverity.INFO,
                    {"proposal_id": str(outcome.proposal_id), "run_id": str(run.id)},
                    category=CATEGORY_TRADING,
                )
            logger.info(
                "agent_completed",
                run_id=str(run.id),
                user_id=str(user.id),
                symbol=outcome.result.symbol,
                provider=outcome.provider,
                model=outcome.model,
                mode=run.mode.value,
                tool_count=len(outcome.tool_calls),
                proposal_id=str(outcome.proposal_id) if outcome.proposal_id else None,
                latency_ms=outcome.latency_ms,
            )
        except TimeoutError:
            await self._fail(run, user, "agent run timed out", timed_out=True)
        except (AgentError, CredentialError) as exc:
            await self._fail(run, user, getattr(exc, "message", str(exc)))
        except Exception:  # noqa: BLE001 - never leak provider internals
            await self._fail(run, user, "agent run failed")
        return run

    async def _build_provider(self, run: AgentRun, user: User):  # noqa: ANN202
        if run.provider_config_id is not None:
            config = await self._providers.get(user.id, run.provider_config_id)
            api_key = self._providers.decrypt_key(config)
            return create_provider(
                provider=config.provider,
                model=config.model,
                api_key=api_key,
                base_url=config.base_url,
                settings=self._settings,
            )
        if self._settings.LLM_API_KEY and self._settings.LLM_MODEL:
            return create_provider(
                provider=self._settings.LLM_PROVIDER,
                model=self._settings.LLM_MODEL,
                api_key=self._settings.LLM_API_KEY,
                base_url=None,
                settings=self._settings,
            )
        raise AgentNotConfiguredError("no LLM provider is configured")

    async def _persist_decision(  # noqa: ANN001
        self, run: AgentRun, result: TradingAnalysisResult, outcome
    ) -> None:
        signal_ids = [signal for signal in result.strategy_signals if signal]
        decision = AgentDecision(
            agent_run_id=run.id,
            portfolio_id=None,
            proposal_id=outcome.proposal_id,
            symbol=result.symbol,
            action=_ACTION_MAP[result.action],
            confidence=result.confidence,
            reasoning_summary=result.summary,
            evidence=[item.model_dump(mode="json") for item in result.supporting_evidence],
            concerns=list(result.concerns),
            proposal_recommended=bool(result.proposal_recommended),
            market_regime=_regime(result.market_regime),
            strategy_signal_ids=signal_ids,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        self._session.add(decision)
        await self._session.flush()

    async def _fail(
        self, run: AgentRun, user: User, message: str, *, timed_out: bool = False
    ) -> None:
        run.status = RunStatus.FAILED
        run.completed_at = datetime.now(UTC)
        run.updated_at = run.completed_at
        run.error = message
        await self._session.flush()
        self._emit("agent.failed", run, extra={"timed_out": timed_out})
        await self._notify(
            user.id,
            "Agent run failed",
            f"Analysis for {(run.symbols or ['asset'])[0]} could not be completed.",
            NotificationSeverity.WARNING,
            {"run_id": str(run.id)},
        )
        logger.warning("agent_failed", run_id=str(run.id), reason=message)

    # --- reads --------------------------------------------------------------
    async def list_runs(
        self, user_id: uuid.UUID, *, limit: int = 50, offset: int = 0
    ) -> tuple[list[AgentRun], int]:
        items = await self._runs.list_for_user(user_id, limit=limit, offset=offset)
        total = await self._runs.count_for_user(user_id)
        return items, total

    async def get_run(self, user_id: uuid.UUID, run_id: uuid.UUID) -> AgentRun:
        run = await self._runs.get_for_user(run_id, user_id)
        if run is None:
            raise NotFoundError(f"Agent run {run_id} not found")
        return run

    async def list_decisions(
        self, user_id: uuid.UUID, *, limit: int = 50, offset: int = 0
    ) -> tuple[list[AgentDecision], int]:
        items = await self._decisions.list_for_user(user_id, limit=limit, offset=offset)
        total = await self._decisions.count_for_user(user_id)
        return items, total

    async def get_decision(self, user_id: uuid.UUID, decision_id: uuid.UUID) -> AgentDecision:
        decision = await self._decisions.get_for_user(decision_id, user_id)
        if decision is None:
            raise NotFoundError(f"Agent decision {decision_id} not found")
        return decision

    # --- helpers ------------------------------------------------------------
    def _emit(self, event: str, run: AgentRun, extra: dict | None = None) -> None:
        data = {
            "run_id": str(run.id),
            "status": run.status.value,
            "symbols": run.symbols or [],
            "provider": run.provider,
            "model": run.model,
            "mode": run.mode.value,
        }
        if extra:
            data.update(extra)
        queue_event(self._session.info, DomainEvent(event=event, data=data, user_id=run.user_id))

    async def _notify(
        self,
        user_id: uuid.UUID,
        title: str,
        message: str,
        severity: NotificationSeverity,
        payload: dict,
        *,
        category: str = CATEGORY_SYSTEM,
    ) -> None:
        await NotificationService(self._session).create_notification(
            user_id=user_id,
            category=category,
            title=title,
            message=message,
            severity=severity,
            payload=payload,
        )


def _regime(value: MarketRegime | None) -> MarketRegime | None:
    return value


def _run_summary(run: AgentRun) -> dict:
    return {
        "id": str(run.id),
        "status": run.status.value,
        "symbols": run.symbols or [],
        "provider": run.provider,
        "model": run.model,
        "mode": run.mode.value,
        "created_at": run.created_at.isoformat() if run.created_at else None,
        "proposal_id": str(run.proposal_id) if run.proposal_id else None,
    }


def _as_decimal(value: Decimal | None) -> Decimal:
    return value if value is not None else Decimal("0")
