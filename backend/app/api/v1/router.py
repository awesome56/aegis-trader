"""API v1 aggregate router."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import auth, health, markets, system

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(system.router)
api_router.include_router(markets.router)

# Phase 3+ routers (portfolio, strategies, risk, orders, agent, backtests,
# notifications, websocket) will be attached here.
