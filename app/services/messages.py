from __future__ import annotations

import csv
import json
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from io import StringIO
from uuid import uuid4

from arq.connections import ArqRedis
from fastapi import HTTPException, status
from sqlalchemy import and_, case, delete, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.core.enums import DeliveryStatus, MessageSource, MessageStatus
from app.core.logging import log_event
from app.core.sanitization import sanitize_for_storage, sanitize_text
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
        selectinload(Message.user),
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
    idempotency_key: str | None = None,
) -> tuple[str, bool]:
    if not push_key.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Push key is disabled")

    idempotency_key = idempotency_key.strip() if idempotency_key else None
    payload_fingerprint = _payload_fingerprint(payload) if idempotency_key else None
    if idempotency_key:
        existing = await session.scalar(
            select(Message).where(
                Message.push_key_id == push_key.id,
                Message.idempotency_key == idempotency_key,
            )
        )
        if existing is not None:
            if existing.idempotency_hash != payload_fingerprint:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Idempotency key already used with a different payload",
                )
            return existing.id, True
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
        request_payload=sanitize_for_storage(payload.model_dump(mode="json")),
        idempotency_key=idempotency_key,
        idempotency_hash=payload_fingerprint,
        status=MessageStatus.QUEUED,
    )
    session.add(message)
    deliveries: list[Delivery] = []
    for channel in channels:
        adapter_payload = sanitize_for_storage(
            build_adapter_payload(channel.type, payload.title, payload.content, payload.type)
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

    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        if not idempotency_key:
            raise exc
        existing = await session.scalar(
            select(Message).where(
                Message.push_key_id == push_key.id,
                Message.idempotency_key == idempotency_key,
            )
        )
        if existing is None:
            raise exc
        if existing.idempotency_hash != payload_fingerprint:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Idempotency key already used with a different payload",
            ) from exc
        return existing.id, True
    for delivery in deliveries:
        await redis.enqueue_job("deliver_message", delivery.id)
    return message_id, False


async def get_message_list(
    session: AsyncSession,
    user: User,
    offset: int = 0,
    limit: int = 50,
    q: str | None = None,
    status_filters: list[MessageStatus] | None = None,
) -> tuple[list[Message], int]:
    query = select(Message).join(PushKey, PushKey.id == Message.push_key_id)
    count_query = (
        select(func.count()).select_from(Message).join(PushKey, PushKey.id == Message.push_key_id)
    )
    if user.role.value != "admin":
        query = query.where(Message.user_id == user.id)
        count_query = count_query.where(Message.user_id == user.id)
    if q:
        pattern = f"%{q.strip()}%"
        query = query.where(
            or_(
                Message.id.ilike(pattern),
                Message.title.ilike(pattern),
                PushKey.business_name.ilike(pattern),
            )
        )
        count_query = count_query.where(
            or_(
                Message.id.ilike(pattern),
                Message.title.ilike(pattern),
                PushKey.business_name.ilike(pattern),
            )
        )
    if status_filters:
        query = query.where(Message.status.in_(status_filters))
        count_query = count_query.where(Message.status.in_(status_filters))

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


async def list_messages_for_export(
    session: AsyncSession,
    user: User,
    q: str | None = None,
    status_filters: list[MessageStatus] | None = None,
) -> list[Message]:
    messages, _ = await get_message_list(
        session,
        user,
        offset=0,
        limit=10_000,
        q=q,
        status_filters=status_filters,
    )
    return messages


def _csv_line(values: list[object]) -> str:
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(values)
    return output.getvalue()


def _payload_fingerprint(payload: PushRequest) -> str:
    return sha256(
        json.dumps(
            payload.model_dump(mode="json", exclude_none=True),
            sort_keys=True,
            ensure_ascii=False,
        ).encode("utf-8")
    ).hexdigest()


def _message_export_query(
    user: User,
    q: str | None = None,
    status_filters: list[MessageStatus] | None = None,
):
    query = (
        select(
            Message.id.label("message_id"),
            PushKey.business_name.label("business_name"),
            Message.title.label("title"),
            Message.message_type.label("message_type"),
            Message.status.label("status"),
            Message.created_at.label("created_at"),
            func.count(Delivery.id).label("delivery_count"),
            func.sum(case((Delivery.status == DeliveryStatus.SUCCESS, 1), else_=0)).label(
                "success_count"
            ),
            func.sum(
                case(
                    (
                        Delivery.status.in_([DeliveryStatus.FAILED, DeliveryStatus.DEAD_LETTER]),
                        1,
                    ),
                    else_=0,
                )
            ).label("failed_count"),
        )
        .join(PushKey, PushKey.id == Message.push_key_id)
        .outerjoin(Delivery, Delivery.message_id == Message.id)
        .group_by(
            Message.id,
            PushKey.business_name,
            Message.title,
            Message.message_type,
            Message.status,
            Message.created_at,
        )
        .order_by(Message.created_at.desc())
    )
    if user.role.value != "admin":
        query = query.where(Message.user_id == user.id)
    if q:
        pattern = f"%{q.strip()}%"
        query = query.where(
            or_(
                Message.id.ilike(pattern),
                Message.title.ilike(pattern),
                PushKey.business_name.ilike(pattern),
            )
        )
    if status_filters:
        query = query.where(Message.status.in_(status_filters))
    return query


async def stream_messages_csv(
    session: AsyncSession,
    user: User,
    q: str | None = None,
    status_filters: list[MessageStatus] | None = None,
):
    yield _csv_line(
        [
            "message_id",
            "business_name",
            "title",
            "message_type",
            "status",
            "delivery_count",
            "success_count",
            "failed_count",
            "created_at",
        ]
    )

    result = await session.stream(_message_export_query(user, q=q, status_filters=status_filters))
    async for row in result:
        yield _csv_line(
            [
                row.message_id,
                row.business_name,
                row.title,
                row.message_type.value,
                row.status.value,
                int(row.delivery_count or 0),
                int(row.success_count or 0),
                int(row.failed_count or 0),
                row.created_at.isoformat(),
            ]
        )


async def update_message_status(session: AsyncSession, message_id: str) -> None:
    message = await session.scalar(
        select(Message).where(Message.id == message_id).options(selectinload(Message.deliveries))
    )
    if message is None:
        return

    statuses = {delivery.status for delivery in message.deliveries}
    if statuses and statuses.issubset({DeliveryStatus.SUCCESS}):
        message.status = MessageStatus.SUCCESS
    elif DeliveryStatus.SUCCESS in statuses and (
        DeliveryStatus.FAILED in statuses or DeliveryStatus.DEAD_LETTER in statuses
    ):
        message.status = MessageStatus.PARTIAL_SUCCESS
    elif statuses and statuses.issubset({DeliveryStatus.FAILED, DeliveryStatus.DEAD_LETTER}):
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
    delivery.final_error = sanitize_text(result.error)
    delivery.attempt_logs = [
        *delivery.attempt_logs,
        {
            "at": datetime.now(UTC).isoformat(),
            "status_code": result.status_code,
            "response_body": result.response_body,
            "error": sanitize_text(result.error),
            "retry_scheduled_in_seconds": retry_delay,
        },
    ]

    if result.success:
        delivery.status = DeliveryStatus.SUCCESS
        delivery.delivered_at = datetime.now(UTC)
        delivery.dead_lettered_at = None
        delivery.next_retry_at = None
    elif retry_delay is not None:
        delivery.status = DeliveryStatus.RETRYING
        delivery.dead_lettered_at = None
        delivery.next_retry_at = datetime.now(UTC) + timedelta(seconds=retry_delay)
    else:
        delivery.status = DeliveryStatus.DEAD_LETTER
        delivery.dead_lettered_at = datetime.now(UTC)
        delivery.next_retry_at = None
    delivery.processing_started_at = None

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
        )
    )


async def get_delivery_for_user(
    session: AsyncSession,
    user: User,
    message_id: str,
    delivery_id: str,
) -> Delivery | None:
    query = (
        select(Delivery)
        .where(Delivery.id == delivery_id, Delivery.message_id == message_id)
        .options(
            selectinload(Delivery.channel),
            selectinload(Delivery.message)
            .selectinload(Message.push_key)
            .selectinload(PushKey.channel_links)
            .selectinload(PushKeyChannel.channel),
        )
    )
    if user.role.value != "admin":
        query = query.join(Message).where(Message.user_id == user.id)
    return await session.scalar(query)


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
    if delivery is None or delivery.status in {DeliveryStatus.SUCCESS, DeliveryStatus.DEAD_LETTER}:
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
        delivery.processing_started_at = None
        delivery.next_retry_at = datetime.now(UTC) + timedelta(seconds=delay)
        await session.commit()
        await redis.enqueue_job("deliver_message", delivery.id, _defer_by=timedelta(seconds=delay))
        await update_message_status(session, delivery.message_id)
        return

    delivery.status = DeliveryStatus.SENDING
    delivery.processing_started_at = datetime.now(UTC)
    await session.commit()
    live_payload = build_adapter_payload(
        channel.type,
        message.title,
        message.content,
        message.message_type,
    )
    result = await send_via_channel(http_client, channel, live_payload)

    retry_delay = None
    if not result.success and result.retryable and delivery.attempt_count < len(RETRY_DELAYS):
        retry_delay = RETRY_DELAYS[delivery.attempt_count]

    await apply_delivery_attempt(session, delivery, result, retry_delay)
    if retry_delay is not None:
        await redis.enqueue_job(
            "deliver_message", delivery.id, _defer_by=timedelta(seconds=retry_delay)
        )
    log_event(
        "delivery_processed",
        delivery_id=delivery.id,
        message_id=delivery.message_id,
        channel_id=delivery.channel_id,
        success=result.success,
        retryable=result.retryable,
        retry_delay=retry_delay,
        status_code=result.status_code,
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


async def replay_message(
    session: AsyncSession,
    redis: ArqRedis,
    user: User,
    message_id: str,
) -> str:
    query = (
        select(Message)
        .where(Message.id == message_id)
        .options(
            selectinload(Message.push_key)
            .selectinload(PushKey.channel_links)
            .selectinload(PushKeyChannel.channel)
        )
    )
    if user.role.value != "admin":
        query = query.where(Message.user_id == user.id)
    message = await session.scalar(query)
    if message is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")
    new_message_id, _ = await enqueue_message(
        session,
        redis,
        message.push_key,
        MessageSource.POST,
        PushRequest(
            title=message.title,
            content=message.content,
            type=message.message_type,
            channel_ids=message.requested_channel_ids,
        ),
    )
    return new_message_id


async def retry_failed_delivery(
    session: AsyncSession,
    redis: ArqRedis,
    user: User,
    message_id: str,
    delivery_id: str,
) -> None:
    delivery = await get_delivery_for_user(session, user, message_id, delivery_id)
    if delivery is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Delivery not found")
    if delivery.status not in {DeliveryStatus.FAILED, DeliveryStatus.DEAD_LETTER}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only failed or dead-letter deliveries can be retried manually",
        )

    delivery.status = DeliveryStatus.QUEUED
    delivery.processing_started_at = None
    delivery.next_retry_at = None
    delivery.delivered_at = None
    delivery.dead_lettered_at = None
    await session.commit()
    await update_message_status(session, delivery.message_id)
    await redis.enqueue_job("deliver_message", delivery.id)


async def repair_stale_deliveries(
    session: AsyncSession,
    redis: ArqRedis,
    *,
    limit: int = 200,
) -> int:
    now = datetime.now(UTC)
    cutoff = now - timedelta(seconds=settings.delivery_stale_after_seconds)
    stale_conditions = [
        and_(
            Delivery.status.in_([DeliveryStatus.PENDING, DeliveryStatus.QUEUED]),
            Delivery.updated_at < cutoff,
        ),
        and_(
            Delivery.status == DeliveryStatus.SENDING,
            Delivery.processing_started_at.is_not(None),
            Delivery.processing_started_at < cutoff,
        ),
        and_(
            Delivery.status == DeliveryStatus.RETRYING,
            Delivery.next_retry_at.is_not(None),
            Delivery.next_retry_at < now,
            Delivery.updated_at < cutoff,
        ),
    ]
    deliveries = list(
        await session.scalars(
            select(Delivery)
            .where(or_(*stale_conditions))
            .order_by(Delivery.updated_at.asc())
            .limit(limit)
        )
    )
    if not deliveries:
        return 0

    message_ids: set[str] = set()
    for delivery in deliveries:
        delivery.status = DeliveryStatus.QUEUED
        delivery.processing_started_at = None
        delivery.next_retry_at = None
        delivery.attempt_logs = [
            *delivery.attempt_logs,
            {
                "at": now.isoformat(),
                "status_code": None,
                "response_body": None,
                "error": "delivery requeued by stale-delivery repair",
                "retry_scheduled_in_seconds": None,
            },
        ]
        message_ids.add(delivery.message_id)

    await session.commit()
    for delivery in deliveries:
        await redis.enqueue_job("deliver_message", delivery.id)
    for message_id in message_ids:
        await update_message_status(session, message_id)
    return len(deliveries)
