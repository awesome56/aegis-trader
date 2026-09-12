"""Portfolio snapshot orchestration.

``create_snapshots_for_all`` is the entry point a scheduler/worker should call on
``PORTFOLIO_SNAPSHOT_INTERVAL_SECONDS``. No scheduler is bundled in V1 (the
``app.workers`` package is a placeholder); to run it periodically either invoke
this from a cron/systemd timer, add an ARQ/Dramatiq task, or hit
``POST /api/v1/portfolio/snapshot`` from an operator job. Snapshot creation is
interval-bucketed and idempotent, so overlapping callers are safe.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.market.services.market_data import MarketDataService
from app.models.portfolio import PortfolioSnapshot
from app.portfolio.service import PortfolioService
from app.repositories.broker_account import BrokerAccountRepository
from app.repositories.portfolio import PortfolioRepository

logger = get_logger(__name__)


async def create_snapshots_for_all(
    session: AsyncSession,
    market: MarketDataService,
    *,
    settings: Settings | None = None,
) -> list[PortfolioSnapshot]:
    settings = settings or get_settings()
    portfolios = await PortfolioRepository(session).list(is_active=True, limit=10_000)
    accounts = BrokerAccountRepository(session)
    created: list[PortfolioSnapshot] = []
    for portfolio in portfolios:
        account = (
            await accounts.get(portfolio.broker_account_id)
            if portfolio.broker_account_id is not None
            else None
        )
        service = PortfolioService(session, portfolio, market, account=account, settings=settings)
        snapshot = await service.create_snapshot()
        created.append(snapshot)
        logger.info(
            "portfolio_snapshot_created",
            portfolio_id=str(portfolio.id),
            snapshot_id=str(snapshot.id),
            equity=str(snapshot.equity),
            cash=str(snapshot.cash),
            position_count=snapshot.position_count,
        )
    return created
