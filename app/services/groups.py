from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.group import UserGroup, UserGroupChannelPermission, UserGroupMember
from app.schemas.groups import GroupCreate, GroupUpdate


def group_load_options():
    return (
        selectinload(UserGroup.members).selectinload(UserGroupMember.user),
        selectinload(UserGroup.channel_permissions),
    )


async def list_groups(
    session: AsyncSession,
    offset: int = 0,
    limit: int = 50,
) -> tuple[list[UserGroup], int]:
    total = await session.scalar(select(func.count()).select_from(UserGroup))
    result = await session.scalars(
        select(UserGroup)
        .options(*group_load_options())
        .order_by(UserGroup.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    return list(result.unique()), int(total or 0)


async def get_group_by_id(session: AsyncSession, group_id: str) -> UserGroup | None:
    return await session.scalar(
        select(UserGroup).where(UserGroup.id == group_id).options(*group_load_options())
    )


async def create_group(session: AsyncSession, payload: GroupCreate) -> UserGroup:
    group = UserGroup(
        name=payload.name,
        description=payload.description,
        is_active=payload.is_active,
    )
    session.add(group)
    await session.commit()
    await session.refresh(group)
    return await get_group_by_id(session, group.id)  # type: ignore[return-value]


async def update_group(
    session: AsyncSession,
    group: UserGroup,
    payload: GroupUpdate,
) -> UserGroup:
    for field in ("name", "description", "is_active"):
        if field in payload.model_fields_set:
            setattr(group, field, getattr(payload, field))
    await session.commit()
    return await get_group_by_id(session, group.id)  # type: ignore[return-value]


async def delete_group(session: AsyncSession, group: UserGroup) -> None:
    await session.delete(group)
    await session.commit()


async def set_group_member(
    session: AsyncSession,
    group: UserGroup,
    user_id: str,
    granted: bool,
) -> UserGroup:
    membership = await session.get(UserGroupMember, {"group_id": group.id, "user_id": user_id})
    if granted and membership is None:
        session.add(UserGroupMember(group_id=group.id, user_id=user_id))
    if not granted and membership is not None:
        await session.delete(membership)
    await session.commit()
    return await get_group_by_id(session, group.id)  # type: ignore[return-value]


async def set_group_channel_permission(
    session: AsyncSession,
    group: UserGroup,
    channel_id: str,
    granted: bool,
) -> UserGroup:
    permission = await session.get(
        UserGroupChannelPermission,
        {"group_id": group.id, "channel_id": channel_id},
    )
    if granted and permission is None:
        session.add(UserGroupChannelPermission(group_id=group.id, channel_id=channel_id))
    if not granted and permission is not None:
        await session.delete(permission)
    await session.commit()
    return await get_group_by_id(session, group.id)  # type: ignore[return-value]
