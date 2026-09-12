"""FastAPI dependencies for the proposal/execution layer."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from app.auth.dependencies import CurrentUser, DbSession
from app.brokers.dependencies import BrokerDep
from app.core.config import get_settings
from app.market.dependencies import MarketDataDep
from app.proposals.order_manager import OrderManager
from app.proposals.service import ProposalService


async def get_proposal_service(
    session: DbSession, market: MarketDataDep, user: CurrentUser
) -> ProposalService:
    return ProposalService(session, market, user, settings=get_settings())


async def get_order_manager(
    session: DbSession, market: MarketDataDep, user: CurrentUser, broker: BrokerDep
) -> OrderManager:
    return OrderManager(session, market, user, broker, settings=get_settings())


ProposalServiceDep = Annotated[ProposalService, Depends(get_proposal_service)]
OrderManagerDep = Annotated[OrderManager, Depends(get_order_manager)]
