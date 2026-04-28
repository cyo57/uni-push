from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import hash_password
from app.models.user import User
from app.schemas.users import UserCreate, UserUpdate


async def list_users(
    session: AsyncSession, offset: int = 0, limit: int = 50
) -> tuple[list[User], int]:
    total = await session.scalar(select(func.count()).select_from(User))
    result = await session.scalars(
        select(User)
        .options(selectinload(User.group_memberships))
        .order_by(User.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    return list(result), int(total or 0)


async def create_user(session: AsyncSession, payload: UserCreate) -> User:
    user = User(
        username=payload.username,
        display_name=payload.display_name,
        password_hash=hash_password(payload.password),
        role=payload.role,
        is_active=True,
        token_version=1,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user, attribute_names=["group_memberships"])
    return user


async def update_user(session: AsyncSession, user: User, payload: UserUpdate) -> User:
    if payload.display_name is not None:
        user.display_name = payload.display_name
    if payload.password is not None:
        user.password_hash = hash_password(payload.password)
        user.token_version += 1
    if payload.role is not None:
        user.role = payload.role
    if payload.is_active is not None:
        user.is_active = payload.is_active
    await session.commit()
    await session.refresh(user, attribute_names=["group_memberships"])
    return user
