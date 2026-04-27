from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import UserRole
from app.core.security import hash_password
from app.models.user import User


async def ensure_admin_user(
    session: AsyncSession,
    username: str,
    password: str,
    display_name: str,
) -> User:
    existing = await session.scalar(select(User).where(User.username == username))
    if existing:
        return existing

    user = User(
        username=username,
        display_name=display_name,
        password_hash=hash_password(password),
        role=UserRole.ADMIN,
        is_active=True,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def reset_user_password(
    session: AsyncSession,
    username: str,
    new_password: str,
) -> User | None:
    user = await session.scalar(select(User).where(User.username == username))
    if user is None:
        return None

    user.password_hash = hash_password(new_password)
    await session.commit()
    await session.refresh(user)
    return user
