"""Idempotent paper account bootstrap."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.brokers.exceptions import BrokerUnavailableError
from app.core.config import Settings, get_settings
from app.models.broker import BrokerAccount
from app.models.enums import BrokerMode
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
