"""FastAPI dependencies for the risk layer."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from app.auth.dependencies import CurrentUser, DbSession
from app.core.config import get_settings
from app.market.dependencies import MarketDataDep
from app.risk.service import RiskEngine
from app.risk.settings_service import RiskSettingsService
from app.risk.trading_state import TradingStateService


async def get_risk_engine(
    session: DbSession, market: MarketDataDep, user: CurrentUser
) -> RiskEngine:
    return RiskEngine(session, market, user)


def get_risk_settings_service(session: DbSession) -> RiskSettingsService:
    return RiskSettingsService(session, get_settings())


def get_trading_state_service(session: DbSession) -> TradingStateService:
    return TradingStateService(session, settings=get_settings())


RiskEngineDep = Annotated[RiskEngine, Depends(get_risk_engine)]
RiskSettingsDep = Annotated[RiskSettingsService, Depends(get_risk_settings_service)]
TradingStateDep = Annotated[TradingStateService, Depends(get_trading_state_service)]
