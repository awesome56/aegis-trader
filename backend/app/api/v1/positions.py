"""Positions REST API (authenticated, owner-scoped valuations)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter

from app.core.exceptions import NotFoundError
from app.portfolio.dependencies import PortfolioDep
from app.portfolio.types import PositionValuation

router = APIRouter(prefix="/positions", tags=["positions"])


@router.get("", response_model=list[PositionValuation], summary="List open positions")
async def list_positions(portfolio: PortfolioDep) -> list[PositionValuation]:
    return await portfolio.positions()


@router.get("/{position_id}", response_model=PositionValuation, summary="Position detail")
async def get_position(position_id: uuid.UUID, portfolio: PortfolioDep) -> PositionValuation:
    position = await portfolio.get_position(position_id)
    if position is None:
        raise NotFoundError(f"Position {position_id} not found")
    return position
