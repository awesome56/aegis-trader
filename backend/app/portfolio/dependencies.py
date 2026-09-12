"""FastAPI dependency for PortfolioService (scoped to the authenticated owner)."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from app.auth.dependencies import CurrentUser, DbSession
from app.brokers.bootstrap import ensure_paper_account
from app.market.dependencies import MarketDataDep
from app.portfolio.service import PortfolioService


async def get_portfolio_service(
    session: DbSession,
    user: CurrentUser,
    market: MarketDataDep,
) -> PortfolioService:
    account, portfolio = await ensure_paper_account(session, user)
    return PortfolioService(session, portfolio, market, account=account)


PortfolioDep = Annotated[PortfolioService, Depends(get_portfolio_service)]
