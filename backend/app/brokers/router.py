"""Broker routing (Phase 10).

Selects the correct adapter for an account/environment. Fails closed: there is
no silent fallback between LIVE and DEMO, and unimplemented providers raise.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.brokers.base import BrokerAdapter
from app.brokers.bootstrap import ensure_paper_account
from app.brokers.exceptions import BrokerConfigurationError
from app.core.config import Settings, get_settings
from app.market.services.market_data import MarketDataService
from app.models.broker import BrokerAccount
from app.models.enums import BrokerEnvironment
from app.models.user import User


class BrokerRouter:
    def __init__(self, session: AsyncSession, settings: Settings | None = None) -> None:
        self._session = session
        self._settings = settings or get_settings()

    async def route(
        self,
        *,
        user: User,
        account: BrokerAccount,
        asset_class: str | None = None,
    ) -> BrokerAdapter:
        if account.user_id != user.id:
            raise BrokerConfigurationError("broker account does not belong to this user")
        if not account.is_active:
            raise BrokerConfigurationError("broker account is not active")
        if account.environment is BrokerEnvironment.LIVE:
            allowed, missing = self._settings.live_trading_allowed()
            if not self._settings.LIVE_TRADING_ALLOWED or not allowed:
                raise BrokerConfigurationError(
                    "live broker routing is locked",
                    details={"missing_requirements": missing or ["LIVE_TRADING_ALLOWED"]},
                )

        provider = account.broker.strip().lower()
        if provider == "paper":
            from app.brokers.paper import PaperBrokerAdapter

            paper_account, portfolio = await ensure_paper_account(
                self._session, user, self._settings
            )
            market = MarketDataService(self._session, settings=self._settings)
            return PaperBrokerAdapter(
                self._session, paper_account, portfolio, market, settings=self._settings
            )
        # No silent fallback to paper for external providers.
        raise BrokerConfigurationError(
            f"broker adapter for provider {provider!r} is not implemented",
            details={"provider": provider, "environment": account.environment.value},
        )
