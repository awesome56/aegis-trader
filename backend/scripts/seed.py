"""Bootstrap the owner account, a paper broker account, and a default portfolio.

Idempotent: safe to run multiple times. This creates real (paper) records; it
does not fabricate market data or trading activity.

Usage:
    python -m scripts.seed --email owner@example.com --password 'strong-password'
"""

from __future__ import annotations

import argparse
import asyncio
from decimal import Decimal

from app.core.config import get_settings
from app.core.security import hash_password
from app.database.session import dispose_engine, get_session_factory
from app.models import BrokerAccount, BrokerMode, Portfolio, User
from sqlalchemy import select


async def seed(email: str, password: str, full_name: str | None) -> None:
    settings = get_settings()
    factory = get_session_factory()
    async with factory() as session:
        user = (
            await session.execute(select(User).where(User.email == email.lower()))
        ).scalar_one_or_none()
        if user is None:
            user = User(
                email=email.lower(),
                hashed_password=hash_password(password),
                full_name=full_name,
                is_superuser=True,
            )
            session.add(user)
            await session.flush()
            print(f"created user {user.email}")
        else:
            print(f"user {user.email} already exists")

        broker = (
            await session.execute(
                select(BrokerAccount).where(
                    BrokerAccount.user_id == user.id, BrokerAccount.mode == BrokerMode.PAPER
                )
            )
        ).scalar_one_or_none()
        if broker is None:
            broker = BrokerAccount(
                user_id=user.id,
                broker="paper",
                account_name="Paper Account",
                mode=BrokerMode.PAPER,
                cash_balance=Decimal(str(settings.PAPER_INITIAL_BALANCE)),
                buying_power=Decimal(str(settings.PAPER_INITIAL_BALANCE)),
            )
            session.add(broker)
            await session.flush()
            print("created paper broker account")

        portfolio = (
            await session.execute(
                select(Portfolio).where(
                    Portfolio.user_id == user.id, Portfolio.is_default.is_(True)
                )
            )
        ).scalar_one_or_none()
        if portfolio is None:
            session.add(
                Portfolio(
                    user_id=user.id,
                    broker_account_id=broker.id,
                    name="Primary Portfolio",
                    base_currency="USD",
                    initial_capital=Decimal(str(settings.PAPER_INITIAL_BALANCE)),
                    cash=Decimal(str(settings.PAPER_INITIAL_BALANCE)),
                    is_default=True,
                )
            )
            print("created default portfolio")

        await session.commit()
    await dispose_engine()


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed bootstrap data")
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--full-name", default=None)
    args = parser.parse_args()
    asyncio.run(seed(args.email, args.password, args.full_name))


if __name__ == "__main__":
    main()
