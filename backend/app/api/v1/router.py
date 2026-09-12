"""API v1 aggregate router."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import auth, health, system

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(system.router)

# Phase 2+ routers (market data, portfolio, strategies, risk, orders, agent,
# backtests, notifications, websocket) will be attached here.
