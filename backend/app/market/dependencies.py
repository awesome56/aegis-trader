"""FastAPI dependencies for the market-data layer."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from app.auth.dependencies import DbSession
from app.market.services.indicator_service import IndicatorService
from app.market.services.market_data import MarketDataService


def get_market_data_service(session: DbSession) -> MarketDataService:
    return MarketDataService(session)


def get_indicator_service() -> IndicatorService:
    return IndicatorService()


MarketDataDep = Annotated[MarketDataService, Depends(get_market_data_service)]
IndicatorDep = Annotated[IndicatorService, Depends(get_indicator_service)]
