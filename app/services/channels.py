from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.channel import Channel, UserChannelPermission
from app.models.user import User
from app.schemas.channels import ChannelCreate, ChannelUpdate


def channel_load_options():
    return (
        selectinload(Channel.user_permissions),
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
        query = query.join(UserChannelPermission).where(UserChannelPermission.user_id == user.id)
        count_query = count_query.join(UserChannelPermission).where(
            UserChannelPermission.user_id == user.id
        )

    query = (
        query.options(*channel_load_options())
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
        secret=payload.secret,
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
    for field in ("name", "webhook_url", "secret", "is_enabled", "per_minute_limit"):
        value = getattr(payload, field)
        if value is not None:
            setattr(channel, field, value)
    await session.commit()
    await session.refresh(channel)
    return await get_channel_by_id(session, channel.id)  # type: ignore[return-value]


async def soft_delete_channel(session: AsyncSession, channel: Channel) -> None:
    channel.is_deleted = True
    channel.is_enabled = False
    await session.commit()


async def set_channel_permission(
    session: AsyncSession,
    channel: Channel,
    user_id: str,
    granted: bool,
) -> Channel:
    permission = await session.get(
        UserChannelPermission, {"user_id": user_id, "channel_id": channel.id}
    )
    if granted and permission is None:
        session.add(UserChannelPermission(user_id=user_id, channel_id=channel.id))
    if not granted and permission is not None:
        await session.delete(permission)
    await session.commit()
    return await get_channel_by_id(session, channel.id)  # type: ignore[return-value]


async def list_authorized_channel_ids(session: AsyncSession, user_id: str) -> set[str]:
    rows = await session.scalars(
        select(UserChannelPermission.channel_id).where(UserChannelPermission.user_id == user_id)
    )
    return set(rows)
