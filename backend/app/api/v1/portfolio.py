"""Portfolio REST API (authenticated, owner-scoped)."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Query

from app.portfolio.dependencies import PortfolioDep
from app.portfolio.types import AllocationBreakdown, PortfolioHistory, PortfolioSummary

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


@router.get("", response_model=PortfolioSummary, summary="Portfolio summary")
async def get_portfolio(portfolio: PortfolioDep) -> PortfolioSummary:
    return await portfolio.summary()


@router.get("/history", response_model=PortfolioHistory, summary="Portfolio equity history")
async def get_history(
    portfolio: PortfolioDep,
    range: Annotated[str, Query(description="1D|1W|1M|3M|6M|YTD|1Y|ALL")] = "1M",
    start: Annotated[datetime | None, Query(description="Custom start (ISO 8601)")] = None,
    end: Annotated[datetime | None, Query(description="Custom end (ISO 8601)")] = None,
) -> PortfolioHistory:
    return await portfolio.history(range, start=start, end=end)


@router.get("/allocation", response_model=AllocationBreakdown, summary="Portfolio allocation")
async def get_allocation(portfolio: PortfolioDep) -> AllocationBreakdown:
    return await portfolio.allocation()
