"""Set or reset a user's password.

Run on the server:

    docker compose --env-file .env.prod -f docker-compose.prod.yml \
        exec -T backend python -m scripts.set_password \
        --email owner@awesometech.com.ng --password 'new-strong-password'

This is how the bootstrap owner rotates the temporary password created by the
seed script.
"""

from __future__ import annotations

import argparse
import asyncio

from app.core.security import hash_password
from app.database.session import dispose_engine, get_session_factory
from app.models import User
from sqlalchemy import select


async def set_password(email: str, password: str) -> None:
    if len(password) < 8:
        raise SystemExit("Password must be at least 8 characters")
    factory = get_session_factory()
    async with factory() as session:
        user = (
            await session.execute(select(User).where(User.email == email.lower()))
        ).scalar_one_or_none()
        if user is None:
            raise SystemExit(f"No user found for {email}")
        user.hashed_password = hash_password(password)
        await session.commit()
        print(f"password updated for {user.email}")
    await dispose_engine()


def main() -> None:
    parser = argparse.ArgumentParser(description="Set a user's password")
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=True)
    args = parser.parse_args()
    asyncio.run(set_password(args.email, args.password))


if __name__ == "__main__":
    main()
