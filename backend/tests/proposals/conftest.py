"""Proposal/execution test fixtures.

Reuses the deterministic risk harness (fixed market provider, paper broker) and
layers the Phase 7 `ProposalService` / `OrderManager` on top of it.
"""

from __future__ import annotations

from decimal import Decimal

import pytest_asyncio
from app.models.enums import OrderType, TradeSide
from app.proposals.order_manager import OrderManager
from app.proposals.service import ProposalService
from app.proposals.types import ProposalCreate

from tests.risk.conftest import risk_env as risk_env_fixture  # noqa: F401

risk_env = risk_env_fixture


def proposal_payload(**overrides: object) -> ProposalCreate:
    defaults: dict[str, object] = {
        "symbol": "AAPL",
        "side": TradeSide.BUY,
        "order_type": OrderType.MARKET,
        "quantity": Decimal("10"),
        "stop_loss": Decimal("130"),
        "take_profit": Decimal("200"),
        "confidence": Decimal("0.9"),
    }
    defaults.update(overrides)
    return ProposalCreate(**defaults)  # type: ignore[arg-type]


@pytest_asyncio.fixture
async def proposal_env(risk_env):  # noqa: ANN001
    async def _build(**settings_overrides: object):
        env = await risk_env(**settings_overrides)
        env.service = ProposalService(
            env.session, env.market, env.user, settings=env.settings, clock=lambda: env.now
        )
        env.manager = OrderManager(
            env.session,
            env.market,
            env.user,
            env.broker,
            settings=env.settings,
            clock=lambda: env.now,
        )
        return env

    return _build
