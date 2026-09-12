"""FastAPI dependency for the strategy service."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from app.auth.dependencies import DbSession
from app.market.dependencies import MarketDataDep
from app.strategies.service import StrategyService


async def get_strategy_service(session: DbSession, market: MarketDataDep) -> StrategyService:
    service = StrategyService(session, market)
    await service.ensure_bootstrapped()
    return service


StrategyDep = Annotated[StrategyService, Depends(get_strategy_service)]
