from __future__ import annotations

from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.enums import UserRole
from app.core.security import generate_push_key, hash_push_key, key_hint
from app.models.channel import Channel
from app.models.message import Delivery, Message
from app.models.push_key import PushKey, PushKeyChannel
from app.models.user import User
from app.schemas.push_keys import PushKeyCreate, PushKeyUpdate
from app.services.channels import list_authorized_channel_ids


def push_key_load_options():
    return (
        selectinload(PushKey.channel_links)
        .selectinload(PushKeyChannel.channel)
        .selectinload(Channel.group_permissions),
        selectinload(PushKey.default_channel),
    )


async def _validate_channel_bindings(
    session: AsyncSession,
    user: User,
    channel_ids: list[str],
    default_channel_id: str,
) -> list[Channel]:
    if default_channel_id not in channel_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Default channel must be bound"
        )

    query = select(Channel).where(
        Channel.id.in_(channel_ids),
        Channel.is_deleted.is_(False),
        Channel.is_enabled.is_(True),
    )
    channels = list(await session.scalars(query))
    if len(channels) != len(set(channel_ids)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="One or more channels are invalid"
        )

    if user.role != UserRole.ADMIN:
        authorized = await list_authorized_channel_ids(session, user.id)
        if not set(channel_ids).issubset(authorized):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You can only bind channels authorized to your account",
            )

    return channels


async def list_push_keys_for_user(
    session: AsyncSession,
    user: User,
    offset: int = 0,
    limit: int = 100,
) -> tuple[list[PushKey], int]:
    query = select(PushKey)
    count_query = select(func.count()).select_from(PushKey)
    if user.role != UserRole.ADMIN:
        query = query.where(PushKey.user_id == user.id)
        count_query = count_query.where(PushKey.user_id == user.id)
    query = (
        query.options(*push_key_load_options())
        .order_by(PushKey.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    total = await session.scalar(count_query)
    rows = await session.scalars(query)
    return list(rows.unique()), int(total or 0)


async def get_push_key_for_user(
    session: AsyncSession, push_key_id: str, user: User
) -> PushKey | None:
    query = select(PushKey).where(PushKey.id == push_key_id).options(*push_key_load_options())
    if user.role != UserRole.ADMIN:
        query = query.where(PushKey.user_id == user.id)
    return await session.scalar(query)


async def create_push_key(
    session: AsyncSession,
    user: User,
    payload: PushKeyCreate,
) -> tuple[PushKey, str]:
    await _validate_channel_bindings(session, user, payload.channel_ids, payload.default_channel_id)
    plaintext_key = generate_push_key()
    push_key = PushKey(
        user_id=user.id,
        business_name=payload.business_name,
        key_hash=hash_push_key(plaintext_key),
        key_hint=key_hint(plaintext_key),
        per_minute_limit=payload.per_minute_limit,
        default_channel_id=payload.default_channel_id,
        is_active=True,
        last_rotated_at=datetime.now(UTC),
    )
    session.add(push_key)
    await session.flush()
    for channel_id in payload.channel_ids:
        session.add(PushKeyChannel(push_key_id=push_key.id, channel_id=channel_id))
    await session.commit()
    stored = await get_push_key_for_user(session, push_key.id, user)
    return stored, plaintext_key  # type: ignore[return-value]


async def update_push_key(
    session: AsyncSession,
    push_key: PushKey,
    actor: User,
    payload: PushKeyUpdate,
) -> PushKey:
    if payload.channel_ids is not None:
        if payload.default_channel_id is None:
            default_channel_id = push_key.default_channel_id
        else:
            default_channel_id = payload.default_channel_id
        await _validate_channel_bindings(session, actor, payload.channel_ids, default_channel_id)
        push_key.channel_links.clear()
        await session.flush()
        for channel_id in payload.channel_ids:
            push_key.channel_links.append(
                PushKeyChannel(push_key_id=push_key.id, channel_id=channel_id)
            )

    if payload.default_channel_id is not None:
        current_channel_ids = {link.channel_id for link in push_key.channel_links}
        if payload.default_channel_id not in current_channel_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Default channel must be in bound channels",
            )
        push_key.default_channel_id = payload.default_channel_id

    if payload.business_name is not None:
        push_key.business_name = payload.business_name
    if payload.per_minute_limit is not None:
        push_key.per_minute_limit = payload.per_minute_limit
    if payload.is_active is not None:
        push_key.is_active = payload.is_active

    await session.commit()
    refreshed = await get_push_key_for_user(session, push_key.id, actor)
    return refreshed  # type: ignore[return-value]


async def rotate_push_key(
    session: AsyncSession, push_key: PushKey, actor: User
) -> tuple[PushKey, str]:
    plaintext_key = generate_push_key()
    push_key.key_hash = hash_push_key(plaintext_key)
    push_key.key_hint = key_hint(plaintext_key)
    push_key.last_rotated_at = datetime.now(UTC)
    await session.commit()
    refreshed = await get_push_key_for_user(session, push_key.id, actor)
    return refreshed, plaintext_key  # type: ignore[return-value]


async def delete_push_key(session: AsyncSession, push_key: PushKey) -> None:
    message_ids = list(
        await session.scalars(select(Message.id).where(Message.push_key_id == push_key.id))
    )
    if message_ids:
        await session.execute(delete(Delivery).where(Delivery.message_id.in_(message_ids)))
        await session.execute(delete(Message).where(Message.id.in_(message_ids)))

    await session.delete(push_key)
    await session.commit()


async def resolve_push_key_by_token(session: AsyncSession, token: str) -> PushKey | None:
    return await session.scalar(
        select(PushKey)
        .where(PushKey.key_hash == hash_push_key(token))
        .options(*push_key_load_options(), selectinload(PushKey.user))
    )
