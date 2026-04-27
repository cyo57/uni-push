from __future__ import annotations

import argparse
import asyncio

from app.db.session import AsyncSessionLocal
from app.services.bootstrap import reset_user_password


async def do_reset_password(username: str, password: str) -> None:
    async with AsyncSessionLocal() as session:
        user = await reset_user_password(session, username, password)
        if user is None:
            raise SystemExit(f"user not found: {username}")
        print(f"Password reset for user: {user.username}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Reset a user's password.")
    parser.add_argument("--username", required=True)
    parser.add_argument("--password", required=True)
    args = parser.parse_args()
    asyncio.run(do_reset_password(args.username, args.password))
