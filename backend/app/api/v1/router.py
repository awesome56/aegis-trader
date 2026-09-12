"""API v1 aggregate router."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import (
    auth,
    broker,
    dashboard,
    health,
    markets,
    notifications,
    portfolio,
    positions,
    risk,
    strategies,
    system,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(system.router)
api_router.include_router(markets.router)
api_router.include_router(dashboard.router)
api_router.include_router(portfolio.router)
api_router.include_router(positions.router)
api_router.include_router(broker.router)
api_router.include_router(notifications.router)
api_router.include_router(strategies.router)
api_router.include_router(risk.router)

# Phase 7+ routers (orders pipeline, agent, backtests) will be attached here.
