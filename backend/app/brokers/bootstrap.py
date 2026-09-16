"""Idempotent broker account and portfolio bootstrap."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.brokers.exceptions import BrokerUnavailableError
from app.core.config import Settings, get_settings
from app.models.broker import BrokerAccount
from app.models.broker_connection import BrokerConnection
from app.models.enums import BrokerEnvironment, BrokerMode
from app.models.portfolio import Portfolio
from app.models.user import User
from app.repositories.broker_account import BrokerAccountRepository
from app.repositories.portfolio import PortfolioRepository

PAPER_BROKER = "paper"


async def ensure_paper_account(
    session: AsyncSession,
    user: User,
    settings: Settings | None = None,
) -> tuple[BrokerAccount, Portfolio]:
    """Return (creating once if needed) the user's paper account and portfolio.

    Idempotent: finds the existing active paper account first, so repeated
    startup/requests never create duplicates.
    """
    settings = settings or get_settings()
    accounts = BrokerAccountRepository(session)
    portfolios = PortfolioRepository(session)

    account = await accounts.get_active_for_user(
        user.id, broker=PAPER_BROKER, mode=BrokerMode.PAPER
    )
    if account is None:
        if not settings.BROKER_PAPER_AUTO_CREATE_ACCOUNT:
            raise BrokerUnavailableError(
                "No paper broker account exists and auto-creation is disabled"
            )
        initial = Decimal(str(settings.PAPER_INITIAL_BALANCE))
        account = BrokerAccount(
            user_id=user.id,
            broker=PAPER_BROKER,
            account_name="Paper Account",
            mode=BrokerMode.PAPER,
            cash_balance=initial,
            buying_power=initial,
            realized_pnl=Decimal("0"),
            currency=settings.BROKER_PAPER_DEFAULT_CURRENCY,
            is_active=True,
        )
        await accounts.add(account)

    portfolio = await portfolios.get_default_for_user(user.id)
    if portfolio is None:
        initial = Decimal(str(settings.PAPER_INITIAL_BALANCE))
        portfolio = Portfolio(
            user_id=user.id,
            broker_account_id=account.id,
            name="Primary Portfolio",
            base_currency=settings.BROKER_PAPER_DEFAULT_CURRENCY,
            cash=Decimal(str(account.cash_balance)),
            initial_capital=initial,
            is_active=True,
            is_default=True,
        )
        await portfolios.add(portfolio)

    return account, portfolio


async def ensure_account_portfolio(session: AsyncSession, account: BrokerAccount) -> Portfolio:
    """Return (creating once) the portfolio that belongs to ``account``.

    External broker accounts get their own portfolio so real-broker positions and
    orders are never mixed into the paper portfolio the rest of the UI treats as
    the default.
    """
    portfolios = PortfolioRepository(session)
    portfolio = await portfolios.get_for_broker_account(account.id)
    if portfolio is None:
        portfolio = Portfolio(
            user_id=account.user_id,
            broker_account_id=account.id,
            name=f"{account.account_name} Portfolio",
            base_currency=account.currency,
            cash=Decimal(str(account.cash_balance or 0)),
            initial_capital=Decimal("0"),
            is_active=True,
            is_default=False,
        )
        await portfolios.add(portfolio)
    return portfolio


async def provision_account_for_connection(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    connection: BrokerConnection,
) -> BrokerAccount | None:
    """Materialise a :class:`BrokerAccount` (and its portfolio) for a connection.

    Idempotent. The internal paper broker returns ``None`` because its account is
    created by :func:`ensure_paper_account`; an account is only ever created for a
    provider that has a real adapter.
    """
    provider = connection.provider.strip().lower()
    if provider == PAPER_BROKER:
        return None

    accounts = BrokerAccountRepository(session)
    account = await accounts.get_for_provider(
        user_id,
        broker=provider,
        environment=connection.environment,
        external_account_id=connection.account_external_id,
    )
    if account is None:
        account = await accounts.get_for_provider(
            user_id, broker=provider, environment=connection.environment
        )

    if account is None:
        account = BrokerAccount(
            user_id=user_id,
            broker=provider,
            account_name=f"{provider.title()} {connection.environment.value}",
            mode=(
                BrokerMode.PAPER
                if connection.environment is BrokerEnvironment.DEMO
                else BrokerMode.LIVE
            ),
            environment=connection.environment,
            external_account_id=connection.account_external_id,
            is_active=True,
            cash_balance=Decimal("0"),
            buying_power=Decimal("0"),
            currency="USD",
        )
        await accounts.add(account)
    elif (
        connection.account_external_id
        and account.external_account_id != connection.account_external_id
    ):
        account.external_account_id = connection.account_external_id
        account.updated_at = datetime.now(UTC)
        await session.flush()

    await ensure_account_portfolio(session, account)
    return account
