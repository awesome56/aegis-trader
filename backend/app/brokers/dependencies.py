"""FastAPI dependencies for the broker layer."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from app.auth.dependencies import CurrentUser, DbSession
from app.brokers.base import BrokerAdapter
from app.brokers.bootstrap import ensure_paper_account
from app.brokers.factory import resolve_broker_provider
from app.brokers.paper import PaperBrokerAdapter
from app.core.config import get_settings
from app.market.dependencies import MarketDataDep


async def get_broker_adapter(
    session: DbSession,
    user: CurrentUser,
    market: MarketDataDep,
) -> BrokerAdapter:
    settings = get_settings()
    resolve_broker_provider(settings)  # fail closed on unsupported providers
    account, portfolio = await ensure_paper_account(session, user, settings)
    return PaperBrokerAdapter(session, account, portfolio, market, settings=settings)


BrokerDep = Annotated[BrokerAdapter, Depends(get_broker_adapter)]
