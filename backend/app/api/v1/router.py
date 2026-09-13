"""API v1 aggregate router."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import (
    activity,
    agent,
    ai,
    auth,
    backtests,
    broker,
    dashboard,
    health,
    markets,
    notifications,
    portfolio,
    positions,
    proposals,
    risk,
    strategies,
    system,
    trades,
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
api_router.include_router(activity.router)
api_router.include_router(trades.router)
api_router.include_router(proposals.router)
api_router.include_router(backtests.router)
api_router.include_router(ai.router)
api_router.include_router(agent.router)

# Phase 7 proposal router is attached in app.api.v1.proposals and included below.
