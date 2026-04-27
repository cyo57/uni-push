from __future__ import annotations

import argparse
import asyncio

from app.core.config import get_settings
from app.db.session import AsyncSessionLocal
from app.services.bootstrap import ensure_admin_user


async def seed_admin(username: str, password: str, display_name: str) -> None:
    async with AsyncSessionLocal() as session:
        user = await ensure_admin_user(session, username, password, display_name)
        print(f"Seeded admin user: {user.username}")


def main() -> None:
    settings = get_settings()
    parser = argparse.ArgumentParser(description="Seed the initial admin user.")
    parser.add_argument("--username", default=settings.bootstrap_admin_username)
    parser.add_argument("--password", default=settings.bootstrap_admin_password)
    parser.add_argument("--display-name", default=settings.bootstrap_admin_display_name)
    args = parser.parse_args()
    asyncio.run(seed_admin(args.username, args.password, args.display_name))
