"""Background worker jobs (Phase 7+).

Everything here is deterministic and paper-safe: snapshot portfolios, evaluate
strategies (persisting signals only) and report open orders. No job may create
orders or bypass the Risk Engine / OrderManager pipeline.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import func, select

from app.brokers.bootstrap import ensure_paper_account
from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.models.enums import OrderStatus
from app.models.order import Order
from app.portfolio.service import PortfolioService
from app.strategies.service import StrategyService
from app.workers.heartbeat import write_heartbeat
from app.workers.lock import LockNotAcquiredError, redis_lock
from app.workers.session import active_users, build_market_service, worker_session

logger = get_logger(__name__)

LOCK_PORTFOLIO_SNAPSHOT = "aegis:worker:lock:portfolio_snapshot"
LOCK_STRATEGY_EVALUATION = "aegis:worker:lock:strategy_evaluation"
LOCK_OPEN_ORDER_MONITOR = "aegis:worker:lock:open_order_monitor"
LOCK_AUTONOMOUS_AGENT = "aegis:worker:lock:autonomous_agent"

_OPEN_STATUSES = [status for status in OrderStatus if not status.is_terminal]


def _settings(ctx: dict[str, Any]) -> Settings:
    return ctx.get("settings") or get_settings()


async def _lock(redis: Any, key: str, settings: Settings) -> Any:  # noqa: ANN401
    return redis_lock(redis, key, ttl_seconds=settings.WORKER_LOCK_TTL_SECONDS)


async def portfolio_snapshot(ctx: dict[str, Any]) -> dict[str, Any]:
    """Snapshot every active user's portfolio (idempotent per interval bucket)."""
    settings = _settings(ctx)
    if ctx.get("redis") is not None:
        try:
            async with await _lock(ctx["redis"], LOCK_PORTFOLIO_SNAPSHOT, settings):
                return await _run_portfolio_snapshot(ctx, settings)
        except LockNotAcquiredError:
            logger.info("worker_job_skipped", job="portfolio_snapshot", reason="locked")
            return {"job": "portfolio_snapshot", "skipped": True}
    return await _run_portfolio_snapshot(ctx, settings)


async def _run_portfolio_snapshot(ctx: dict[str, Any], settings: Settings) -> dict[str, Any]:
    count = 0
    async with worker_session() as session:
        market = build_market_service(session)
        for user in await active_users(session):
            account, portfolio = await ensure_paper_account(session, user, settings)
            service = PortfolioService(
                session, portfolio, market, account=account, settings=settings
            )
            await service.create_snapshot()
            count += 1
    if ctx.get("redis") is not None:
        await write_heartbeat(ctx["redis"], settings)
    logger.info("worker_job_done", job="portfolio_snapshot", portfolios=count, source="worker")
    return {"job": "portfolio_snapshot", "portfolios": count}


async def evaluate_strategies(ctx: dict[str, Any]) -> dict[str, Any]:
    """Evaluate configured strategies and persist de-duplicated signals only."""
    settings = _settings(ctx)
    if ctx.get("redis") is not None:
        try:
            async with await _lock(ctx["redis"], LOCK_STRATEGY_EVALUATION, settings):
                return await _run_evaluate_strategies(ctx, settings)
        except LockNotAcquiredError:
            logger.info("worker_job_skipped", job="strategy_evaluation", reason="locked")
            return {"job": "strategy_evaluation", "skipped": True}
    return await _run_evaluate_strategies(ctx, settings)


async def _run_evaluate_strategies(ctx: dict[str, Any], settings: Settings) -> dict[str, Any]:
    from app.market.validation import detect_asset_class

    if not settings.STRATEGY_EVALUATION_ENABLED:
        return {"job": "strategy_evaluation", "skipped": True, "reason": "disabled"}

    timeframe = settings.strategy_evaluation_timeframe
    evaluated = 0
    signals = 0
    symbols_evaluated: list[str] = []
    skip_reasons: dict[str, int] = {}
    failed: list[str] = []

    async with worker_session() as session:
        market = build_market_service(session)
        service = StrategyService(session, market, settings=settings)
        await service.ensure_bootstrapped()
        for symbol in settings.strategy_evaluation_symbols:
            asset_class = detect_asset_class(symbol)
            provider = market.routed_provider_name(symbol)
            try:
                results = await service.evaluate(symbol, timeframe, persist=True)
            except Exception as exc:  # noqa: BLE001 - one symbol must not stop the sweep
                failed.append(symbol)
                logger.warning(
                    "worker_symbol_failed",
                    symbol=symbol,
                    asset_class=asset_class.value,
                    provider=provider,
                    timeframe=timeframe,
                    error=str(exc),
                )
                continue
            symbol_signals = 0
            for result in results:
                if result.signal is not None:
                    signals += 1
                    symbol_signals += 1
                else:
                    skip_reasons[result.status.value] = skip_reasons.get(result.status.value, 0) + 1
            evaluated += len(results)
            symbols_evaluated.append(symbol)
            logger.info(
                "worker_strategy_symbol",
                symbol=symbol,
                asset_class=asset_class.value,
                provider=provider,
                timeframe=timeframe,
                results=len(results),
                signals=symbol_signals,
            )

    if ctx.get("redis") is not None:
        await write_heartbeat(ctx["redis"], settings)
    logger.info(
        "worker_job_done",
        job="strategy_evaluation",
        evaluated=evaluated,
        signals=signals,
        symbols=len(symbols_evaluated),
    )
    return {
        "job": "strategy_evaluation",
        "timeframe": timeframe,
        "evaluated": evaluated,
        "signals": signals,
        "symbols": symbols_evaluated,
        "skip_reasons": skip_reasons,
        "failed_symbols": failed,
    }


async def monitor_open_orders(ctx: dict[str, Any]) -> dict[str, Any]:
    """Count non-terminal orders; paper fills are synchronous so this is a probe."""
    settings = _settings(ctx)
    if ctx.get("redis") is not None:
        try:
            async with await _lock(ctx["redis"], LOCK_OPEN_ORDER_MONITOR, settings):
                return await _run_monitor_open_orders(ctx, settings)
        except LockNotAcquiredError:
            logger.info("worker_job_skipped", job="open_order_monitor", reason="locked")
            return {"job": "open_order_monitor", "skipped": True}
    return await _run_monitor_open_orders(ctx, settings)


async def _run_monitor_open_orders(ctx: dict[str, Any], settings: Settings) -> dict[str, Any]:
    async with worker_session() as session:
        open_orders = int(
            await session.scalar(
                select(func.count()).select_from(Order).where(Order.status.in_(_OPEN_STATUSES))
            )
            or 0
        )
    if ctx.get("redis") is not None:
        await write_heartbeat(ctx["redis"], settings)
    return {"job": "open_order_monitor", "open_orders": open_orders}


async def run_autonomous_agent(ctx: dict[str, Any]) -> dict[str, Any]:
    """Periodic autonomous agent cycle (DEMO-first; live remains gated).

    For every enabled auto-trading policy: evaluate its symbol universe and let
    the agent act (analysis/propose/auto-trade) through the safety gateway.
    """
    settings = _settings(ctx)
    if not settings.AUTO_TRADING_AGENT_ENABLED:
        return {"job": "autonomous_agent", "skipped": True, "reason": "disabled"}
    if ctx.get("redis") is not None:
        try:
            async with await _lock(ctx["redis"], LOCK_AUTONOMOUS_AGENT, settings):
                return await _run_autonomous_agent(ctx, settings)
        except LockNotAcquiredError:
            logger.info("worker_job_skipped", job="autonomous_agent", reason="locked")
            return {"job": "autonomous_agent", "skipped": True, "reason": "locked"}
    return await _run_autonomous_agent(ctx, settings)


async def _run_autonomous_agent(ctx: dict[str, Any], settings: Settings) -> dict[str, Any]:
    from app.agents.service import AgentService
    from app.models.enums import AgentMode
    from app.repositories.auto_trading import AutoTradingPolicyRepository
    from app.repositories.broker_account import BrokerAccountRepository

    runs = 0
    failed = 0
    symbols_processed = 0
    timeframe = settings.strategy_evaluation_timeframe

    async with worker_session() as session:
        policies = await AutoTradingPolicyRepository(session).list_enabled()
        for policy in policies:
            account = await BrokerAccountRepository(session).get(policy.broker_account_id)
            if account is None or not account.is_active:
                continue
            symbols = list(policy.allowed_symbols or settings.strategy_evaluation_symbols)[:5]
            for symbol in symbols:
                lock_key = f"autotrade:{account.id}:{symbol}"
                acquired = None
                if ctx.get("redis") is not None:
                    acquired = redis_lock(
                        ctx["redis"], lock_key, ttl_seconds=settings.AGENT_RUN_TIMEOUT_SECONDS + 30
                    )
                try:
                    if acquired is not None:
                        await acquired.__aenter__()
                    service = AgentService(session, settings)
                    run = await service.create_run(
                        user_id=policy.user_id,
                        symbol=symbol,
                        timeframe=timeframe,
                        mode=AgentMode.AUTO_TRADE,
                        broker_account_id=account.id,
                        question=(
                            "Autonomous cycle: inspect account, positions and orders; "
                            "act only if evidence is strong, otherwise HOLD."
                        ),
                    )
                    await service.execute(run.id)
                    runs += 1
                    symbols_processed += 1
                except Exception as exc:  # noqa: BLE001 - one symbol must not stop the cycle
                    failed += 1
                    logger.warning(
                        "autonomous_agent_symbol_failed", symbol=symbol, error=str(exc)
                    )
                finally:
                    if acquired is not None:
                        await acquired.__aexit__(None, None, None)

    if ctx.get("redis") is not None:
        await write_heartbeat(ctx["redis"], settings)
    logger.info(
        "worker_job_done",
        job="autonomous_agent",
        runs=runs,
        failed=failed,
        symbols=symbols_processed,
    )
    return {"job": "autonomous_agent", "runs": runs, "failed": failed}


async def run_backtest(ctx: dict[str, Any], backtest_id: str) -> dict[str, Any]:
    """Execute a queued backtest. Idempotent: a completed run returns unchanged."""
    import uuid

    from app.backtesting.service import BacktestService

    settings = _settings(ctx)
    async with worker_session() as session:
        backtest = await BacktestService(session, settings).execute(uuid.UUID(backtest_id))
        status = backtest.status.value
    if ctx.get("redis") is not None:
        await write_heartbeat(ctx["redis"], settings)
    logger.info("worker_job_done", job="run_backtest", backtest_id=backtest_id, status=status)
    return {"job": "run_backtest", "backtest_id": backtest_id, "status": status}


async def run_agent(ctx: dict[str, Any], run_id: str) -> dict[str, Any]:
    """Execute a queued TradingAnalysisAgent run (analysis / propose only)."""
    import uuid

    from app.agents.service import AgentService

    settings = _settings(ctx)
    async with worker_session() as session:
        run = await AgentService(session, settings).execute(uuid.UUID(run_id))
        status = run.status.value
        proposal_id = str(run.proposal_id) if run.proposal_id else None
    if ctx.get("redis") is not None:
        await write_heartbeat(ctx["redis"], settings)
    logger.info("worker_job_done", job="run_agent", run_id=run_id, status=status)
    return {"job": "run_agent", "run_id": run_id, "status": status, "proposal_id": proposal_id}
