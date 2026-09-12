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
    evaluated = 0
    signals = 0
    failed: list[str] = []
    async with worker_session() as session:
        market = build_market_service(session)
        service = StrategyService(session, market, settings=settings)
        await service.ensure_bootstrapped()
        for symbol in settings.worker_strategy_symbols:
            try:
                results = await service.evaluate(symbol, persist=True)
            except Exception as exc:  # noqa: BLE001 - one symbol must not stop the sweep
                failed.append(symbol)
                logger.warning("worker_symbol_failed", symbol=symbol, error=str(exc))
                continue
            evaluated += len(results)
            signals += sum(1 for result in results if result.signal is not None)
    if ctx.get("redis") is not None:
        await write_heartbeat(ctx["redis"], settings)
    logger.info("worker_job_done", job="strategy_evaluation", evaluated=evaluated, signals=signals)
    return {
        "job": "strategy_evaluation",
        "evaluated": evaluated,
        "signals": signals,
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
