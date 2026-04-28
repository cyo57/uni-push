from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import hash_password
from app.models.group import UserGroup, UserGroupMember
from app.models.user import User
from app.schemas.users import UserCreate, UserUpdate


async def list_users(
    session: AsyncSession,
    offset: int = 0,
    limit: int = 50,
    q: str | None = None,
    roles: list[str] | None = None,
    statuses: list[bool] | None = None,
    group_ids: list[str] | None = None,
) -> tuple[list[User], int]:
    query = select(User)
    count_query = select(func.count(func.distinct(User.id))).select_from(User)

    if q:
        pattern = f"%{q.strip()}%"
        query = query.where(User.username.ilike(pattern) | User.display_name.ilike(pattern))
        count_query = count_query.where(
            User.username.ilike(pattern) | User.display_name.ilike(pattern)
        )

    if roles:
        query = query.where(User.role.in_(roles))
        count_query = count_query.where(User.role.in_(roles))

    if statuses:
        query = query.where(User.is_active.in_(statuses))
        count_query = count_query.where(User.is_active.in_(statuses))

    if group_ids:
        query = query.join(UserGroupMember, UserGroupMember.user_id == User.id).where(
            UserGroupMember.group_id.in_(group_ids)
        )
        count_query = count_query.join(UserGroupMember, UserGroupMember.user_id == User.id).where(
            UserGroupMember.group_id.in_(group_ids)
        )

    total = await session.scalar(count_query)
    result = await session.scalars(
        query.options(selectinload(User.group_memberships))
        .distinct()
        .order_by(User.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    return list(result.unique()), int(total or 0)


async def _sync_user_groups(session: AsyncSession, user: User, group_ids: list[str]) -> None:
    normalized_group_ids = list(dict.fromkeys(group_ids))
    if normalized_group_ids:
        found_ids = set(
            await session.scalars(select(UserGroup.id).where(UserGroup.id.in_(normalized_group_ids)))
        )
        if len(found_ids) != len(normalized_group_ids):
            raise ValueError("One or more groups are invalid")

    current_memberships = user.__dict__.get("group_memberships", [])
    current_group_ids = {membership.group_id for membership in current_memberships}

    for membership in list(current_memberships):
        if membership.group_id not in normalized_group_ids:
            await session.delete(membership)

    for group_id in normalized_group_ids:
        if group_id not in current_group_ids:
            session.add(UserGroupMember(group_id=group_id, user_id=user.id))


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
    await session.flush()
    await _sync_user_groups(session, user, payload.group_ids)
    await session.commit()
    await session.refresh(user, attribute_names=["group_memberships"])
    return user


async def update_user(session: AsyncSession, user: User, payload: UserUpdate) -> User:
    await session.refresh(user, attribute_names=["group_memberships"])
    if payload.display_name is not None:
        user.display_name = payload.display_name
    if payload.password is not None:
        user.password_hash = hash_password(payload.password)
        user.token_version += 1
    if payload.role is not None:
        user.role = payload.role
    if payload.is_active is not None:
        user.is_active = payload.is_active
    if payload.group_ids is not None:
        await _sync_user_groups(session, user, payload.group_ids)
    await session.commit()
    await session.refresh(user, attribute_names=["group_memberships"])
    return user
