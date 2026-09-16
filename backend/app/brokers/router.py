"""Broker routing (Phase 10).

Selects the correct adapter for an account/environment. Fails closed: there is
no silent fallback between LIVE and DEMO, and unimplemented providers raise.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.brokers.base import BrokerAdapter
from app.brokers.bootstrap import ensure_account_portfolio, ensure_paper_account
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
        if provider == "alpaca":
            from app.brokers.alpaca.adapter import AlpacaBrokerAdapter
            from app.brokers.alpaca.client import AlpacaClient
            from app.brokers.connections import BrokerConnectionService
            from app.repositories.broker_connection import BrokerConnectionRepository

            connection = await BrokerConnectionRepository(
                self._session
            ).get_default_for_provider(user.id, provider, account.environment)
            if connection is None:
                raise BrokerConfigurationError(
                    "no enabled Alpaca connection for this environment",
                    details={"provider": provider, "environment": account.environment.value},
                )
            service = BrokerConnectionService(self._session, self._settings)
            api_key = service.decrypt_api_key(connection)
            api_secret = service.decrypt_api_secret(connection)
            if not api_key or not api_secret:
                raise BrokerConfigurationError(
                    "Alpaca connection is missing credentials",
                    details={"provider": provider},
                )
            client = AlpacaClient(
                api_key=api_key, api_secret=api_secret, environment=account.environment
            )
            portfolio = await ensure_account_portfolio(self._session, account)
            return AlpacaBrokerAdapter(
                self._session, account, portfolio, client, settings=self._settings
            )

        # No silent fallback to paper for external providers.
        raise BrokerConfigurationError(
            f"broker adapter for provider {provider!r} is not implemented",
            details={"provider": provider, "environment": account.environment.value},
        )
