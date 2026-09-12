"""Trade read API (authenticated, portfolio-scoped)."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select

from app.auth.dependencies import CurrentUser, DbSession, get_current_user
from app.brokers.bootstrap import ensure_paper_account
from app.core.config import get_settings
from app.core.exceptions import NotFoundError
from app.models.order import Trade
from app.schemas.trade import TradePageSchema, TradeSchema

router = APIRouter(prefix="/trades", tags=["trades"], dependencies=[Depends(get_current_user)])


@router.get("", response_model=TradePageSchema, summary="List completed trades")
async def list_trades(
    session: DbSession,
    user: CurrentUser,
    symbol: Annotated[str | None, Query()] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200)] = 50,
) -> TradePageSchema:
    _, portfolio = await ensure_paper_account(session, user, get_settings())
    stmt = select(Trade).where(Trade.portfolio_id == portfolio.id)
    if symbol is not None:
        stmt = stmt.where(Trade.symbol == symbol.strip().upper())
    total = int(
        await session.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    )
    rows = await session.execute(
        stmt.order_by(Trade.opened_at.desc()).limit(page_size).offset((page - 1) * page_size)
    )
    return TradePageSchema(
        items=[TradeSchema.model_validate(row) for row in rows.scalars().all()],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{trade_id}", response_model=TradeSchema, summary="Trade detail")
async def get_trade(trade_id: uuid.UUID, session: DbSession, user: CurrentUser) -> TradeSchema:
    _, portfolio = await ensure_paper_account(session, user, get_settings())
    trade = await session.get(Trade, trade_id)
    if trade is None or trade.portfolio_id != portfolio.id:
        raise NotFoundError(f"Trade {trade_id} not found")
    return TradeSchema.model_validate(trade)
