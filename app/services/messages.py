from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from arq.connections import ArqRedis
from fastapi import HTTPException, status
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.core.enums import DeliveryStatus, MessageSource, MessageStatus
from app.core.security import generate_message_id
from app.models.channel import Channel
from app.models.message import Delivery, Message
from app.models.push_key import PushKey, PushKeyChannel
from app.models.user import User
from app.schemas.channels import ChannelTestRequest
from app.schemas.messages import PushRequest
from app.services.adapters import AdapterSendResult, build_adapter_payload, send_via_channel
from app.services.rate_limit import allow_rate_limit

settings = get_settings()
RETRY_DELAYS = [30, 120, 600]


def message_load_options():
    return (
        selectinload(Message.push_key),
        selectinload(Message.deliveries).selectinload(Delivery.channel),
    )


async def resolve_push_targets(
    push_key: PushKey, requested_channel_ids: list[str] | None
) -> list[Channel]:
    active_channels = {
        link.channel_id: link.channel
        for link in push_key.channel_links
        if link.channel.is_enabled and not link.channel.is_deleted
    }
    if not active_channels:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="No active channels bound to this key"
        )

    if not requested_channel_ids:
        default_channel = active_channels.get(push_key.default_channel_id)
        if default_channel is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Default channel is unavailable"
            )
        return [default_channel]

    if not set(requested_channel_ids).issubset(active_channels):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Requested channels are invalid"
        )
    return [active_channels[channel_id] for channel_id in requested_channel_ids]


async def enforce_key_rate_limit(redis: ArqRedis, push_key: PushKey) -> None:
    allowed, _, ttl = await allow_rate_limit(
        redis,
        f"ratelimit:push-key:{push_key.id}:{datetime.now(UTC).strftime('%Y%m%d%H%M')}",
        push_key.per_minute_limit,
    )
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Push key rate limit exceeded. Retry in {max(ttl, 1)} seconds.",
        )


async def enqueue_message(
    session: AsyncSession,
    redis: ArqRedis,
    push_key: PushKey,
    source: MessageSource,
    payload: PushRequest,
) -> str:
    if not push_key.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Push key is disabled")

    channels = await resolve_push_targets(push_key, payload.channel_ids)
    await enforce_key_rate_limit(redis, push_key)

    message_id = generate_message_id()
    message = Message(
        id=message_id,
        user_id=push_key.user_id,
        push_key_id=push_key.id,
        source=source,
        title=payload.title,
        content=payload.content,
        message_type=payload.type,
        requested_channel_ids=[channel.id for channel in channels],
        request_payload=payload.model_dump(mode="json"),
        status=MessageStatus.QUEUED,
    )
    session.add(message)
    deliveries: list[Delivery] = []
    for channel in channels:
        adapter_payload = build_adapter_payload(
            channel.type, payload.title, payload.content, payload.type
        )
        delivery = Delivery(
            id=str(uuid4()),
            message_id=message_id,
            channel_id=channel.id,
            status=DeliveryStatus.QUEUED,
            adapter_payload=adapter_payload,
            attempt_logs=[],
        )
        deliveries.append(delivery)
        session.add(delivery)

    await session.commit()
    for delivery in deliveries:
        await redis.enqueue_job("deliver_message", delivery.id)
    return message_id


async def get_message_list(
    session: AsyncSession,
    user: User,
    offset: int = 0,
    limit: int = 50,
) -> tuple[list[Message], int]:
    query = select(Message)
    count_query = select(func.count()).select_from(Message)
    if user.role.value != "admin":
        query = query.where(Message.user_id == user.id)
        count_query = count_query.where(Message.user_id == user.id)

    query = (
        query.options(*message_load_options())
        .order_by(Message.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    total = await session.scalar(count_query)
    rows = await session.scalars(query)
    return list(rows.unique()), int(total or 0)


async def get_message_detail(session: AsyncSession, user: User, message_id: str) -> Message | None:
    query = select(Message).where(Message.id == message_id).options(*message_load_options())
    if user.role.value != "admin":
        query = query.where(Message.user_id == user.id)
    return await session.scalar(query)


async def update_message_status(session: AsyncSession, message_id: str) -> None:
    message = await session.scalar(
        select(Message).where(Message.id == message_id).options(selectinload(Message.deliveries))
    )
    if message is None:
        return

    statuses = {delivery.status for delivery in message.deliveries}
    if statuses and statuses.issubset({DeliveryStatus.SUCCESS}):
        message.status = MessageStatus.SUCCESS
    elif DeliveryStatus.SUCCESS in statuses and DeliveryStatus.FAILED in statuses:
        message.status = MessageStatus.PARTIAL_SUCCESS
    elif statuses and statuses.issubset({DeliveryStatus.FAILED}):
        message.status = MessageStatus.FAILED
    else:
        message.status = MessageStatus.PROCESSING
    await session.commit()


async def apply_delivery_attempt(
    session: AsyncSession,
    delivery: Delivery,
    result: AdapterSendResult,
    retry_delay: int | None,
) -> None:
    delivery.attempt_count += 1
    delivery.last_response_status = result.status_code
    delivery.last_response_body = result.response_body
    delivery.final_error = result.error
    delivery.attempt_logs = [
        *delivery.attempt_logs,
        {
            "at": datetime.now(UTC).isoformat(),
            "status_code": result.status_code,
            "response_body": result.response_body,
            "error": result.error,
            "retry_scheduled_in_seconds": retry_delay,
        },
    ]

    if result.success:
        delivery.status = DeliveryStatus.SUCCESS
        delivery.delivered_at = datetime.now(UTC)
        delivery.next_retry_at = None
    elif retry_delay is not None:
        delivery.status = DeliveryStatus.RETRYING
        delivery.next_retry_at = datetime.now(UTC) + timedelta(seconds=retry_delay)
    else:
        delivery.status = DeliveryStatus.FAILED
        delivery.next_retry_at = None

    await session.commit()
    await update_message_status(session, delivery.message_id)


async def load_delivery(session: AsyncSession, delivery_id: str) -> Delivery | None:
    return await session.scalar(
        select(Delivery)
        .where(Delivery.id == delivery_id)
        .options(
            selectinload(Delivery.channel),
            selectinload(Delivery.message)
            .selectinload(Message.push_key)
            .selectinload(PushKey.channel_links)
            .selectinload(PushKeyChannel.channel)
            .selectinload(Channel.user_permissions),
        )
    )


async def maybe_delay_for_channel_limit(redis: ArqRedis, channel: Channel) -> int | None:
    allowed, _, ttl = await allow_rate_limit(
        redis,
        f"ratelimit:channel:{channel.id}:{datetime.now(UTC).strftime('%Y%m%d%H%M')}",
        channel.per_minute_limit,
    )
    if allowed:
        return None
    return max(ttl, 1) + 1


async def process_delivery(
    session: AsyncSession,
    redis: ArqRedis,
    http_client,
    delivery_id: str,
) -> None:
    delivery = await load_delivery(session, delivery_id)
    if delivery is None or delivery.status == DeliveryStatus.SUCCESS:
        return

    channel = delivery.channel
    message = delivery.message
    if not channel.is_enabled or channel.is_deleted or not message.push_key.is_active:
        await apply_delivery_attempt(
            session,
            delivery,
            AdapterSendResult(
                success=False,
                retryable=False,
                status_code=None,
                response_body=None,
                error="Channel or push key disabled",
            ),
            retry_delay=None,
        )
        return

    delay = await maybe_delay_for_channel_limit(redis, channel)
    if delay is not None:
        delivery.status = DeliveryStatus.RETRYING
        delivery.next_retry_at = datetime.now(UTC) + timedelta(seconds=delay)
        await session.commit()
        await redis.enqueue_job("deliver_message", delivery.id, _defer_by=timedelta(seconds=delay))
        await update_message_status(session, delivery.message_id)
        return

    delivery.status = DeliveryStatus.SENDING
    await session.commit()
    result = await send_via_channel(http_client, channel, delivery.adapter_payload)

    retry_delay = None
    if not result.success and result.retryable and delivery.attempt_count < len(RETRY_DELAYS):
        retry_delay = RETRY_DELAYS[delivery.attempt_count]

    await apply_delivery_attempt(session, delivery, result, retry_delay)
    if retry_delay is not None:
        await redis.enqueue_job(
            "deliver_message", delivery.id, _defer_by=timedelta(seconds=retry_delay)
        )


async def test_channel(
    channel: Channel, payload: ChannelTestRequest, http_client
) -> AdapterSendResult:
    adapter_payload = build_adapter_payload(
        channel.type, payload.title, payload.content, payload.type
    )
    return await send_via_channel(http_client, channel, adapter_payload)


async def cleanup_expired_messages(session: AsyncSession) -> int:
    cutoff = datetime.now(UTC) - timedelta(days=settings.log_retention_days)
    old_ids = list(await session.scalars(select(Message.id).where(Message.created_at < cutoff)))
    if not old_ids:
        return 0
    await session.execute(delete(Message).where(Message.id.in_(old_ids)))
    await session.commit()
    return len(old_ids)
