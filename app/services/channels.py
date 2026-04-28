from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.crypto import encrypt_secret
from app.models.channel import Channel
from app.models.group import UserGroupChannelPermission, UserGroupMember
from app.models.user import User
from app.schemas.channels import ChannelCreate, ChannelUpdate


def channel_load_options():
    return (
        selectinload(Channel.group_permissions),
        selectinload(Channel.created_by),
    )


async def list_channels_for_user(
    session: AsyncSession,
    user: User,
    offset: int = 0,
    limit: int = 100,
) -> tuple[list[Channel], int]:
    query = select(Channel).where(Channel.is_deleted.is_(False))
    count_query = select(func.count()).select_from(Channel).where(Channel.is_deleted.is_(False))
    if user.role.value != "admin":
        authorized_channel_ids = await list_authorized_channel_ids(session, user.id)
        if not authorized_channel_ids:
            return [], 0
        query = query.where(Channel.id.in_(authorized_channel_ids))
        count_query = count_query.where(Channel.id.in_(authorized_channel_ids))

    query = (
        query.options(*channel_load_options())
        .distinct()
        .order_by(Channel.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    total = await session.scalar(count_query)
    items = await session.scalars(query)
    return list(items.unique()), int(total or 0)


async def get_channel_by_id(session: AsyncSession, channel_id: str) -> Channel | None:
    result = await session.scalar(
        select(Channel)
        .where(Channel.id == channel_id, Channel.is_deleted.is_(False))
        .options(*channel_load_options())
    )
    return result


async def create_channel(session: AsyncSession, user: User, payload: ChannelCreate) -> Channel:
    channel = Channel(
        name=payload.name,
        type=payload.type,
        webhook_url=payload.webhook_url,
        secret=encrypt_secret(payload.secret),
        is_enabled=payload.is_enabled,
        per_minute_limit=payload.per_minute_limit,
        created_by_id=user.id,
    )
    session.add(channel)
    await session.commit()
    await session.refresh(channel)
    return await get_channel_by_id(session, channel.id)  # type: ignore[return-value]


async def update_channel(
    session: AsyncSession, channel: Channel, payload: ChannelUpdate
) -> Channel:
    for field in ("name", "webhook_url", "is_enabled", "per_minute_limit"):
        if field in payload.model_fields_set:
            setattr(channel, field, getattr(payload, field))

    if "secret" in payload.model_fields_set:
        channel.secret = encrypt_secret(payload.secret)

    await session.commit()
    await session.refresh(channel)
    return await get_channel_by_id(session, channel.id)  # type: ignore[return-value]


async def soft_delete_channel(session: AsyncSession, channel: Channel) -> None:
    channel.is_deleted = True
    channel.is_enabled = False
    await session.commit()


async def list_authorized_channel_ids(session: AsyncSession, user_id: str) -> set[str]:
    group_rows = await session.scalars(
        select(UserGroupChannelPermission.channel_id)
        .join(UserGroupMember, UserGroupMember.group_id == UserGroupChannelPermission.group_id)
        .where(UserGroupMember.user_id == user_id)
    )
    return set(group_rows)
