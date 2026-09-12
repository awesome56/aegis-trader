"""Dashboard REST API: one aggregated response for the web/mobile dashboards."""

from __future__ import annotations

from fastapi import APIRouter

from app.auth.dependencies import CurrentUser, DbSession
from app.dashboard.service import DashboardService
from app.market.dependencies import MarketDataDep
from app.schemas.dashboard import DashboardSchema

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard", response_model=DashboardSchema, summary="Aggregated dashboard data")
async def get_dashboard(
    session: DbSession,
    user: CurrentUser,
    market: MarketDataDep,
) -> DashboardSchema:
    return await DashboardService(session, user, market).build()
