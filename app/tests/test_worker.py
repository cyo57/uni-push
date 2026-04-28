from datetime import UTC, datetime
from uuid import uuid4

import httpx
from sqlalchemy import select

from app.core.enums import (
    ChannelType,
    DeliveryStatus,
    MessageSource,
    MessageStatus,
    MessageType,
    UserRole,
)
from app.core.security import hash_password
from app.models.channel import Channel
from app.models.message import Delivery, Message
from app.models.push_key import PushKey, PushKeyChannel
from app.models.user import User
from app.services.messages import process_delivery, repair_stale_deliveries
from app.services.rate_limit import allow_rate_limit


async def seed_delivery(session_factory):
    async with session_factory() as session:
        user = User(
            username="worker-user",
            display_name="Worker User",
            password_hash=hash_password("worker-pass"),
            role=UserRole.USER,
            is_active=True,
        )
        channel = Channel(
            name=f"worker-{uuid4()}",
            type=ChannelType.DINGTALK_BOT,
            webhook_url="https://example.test/worker",
            secret="secret",
            is_enabled=True,
            per_minute_limit=1,
        )
        session.add_all([user, channel])
        await session.flush()
        push_key = PushKey(
            user_id=user.id,
            business_name="worker",
            key_hash="hash",
            key_hint="hint",
            is_active=True,
            per_minute_limit=5,
            default_channel_id=channel.id,
        )
        session.add(push_key)
        await session.flush()
        session.add(PushKeyChannel(push_key_id=push_key.id, channel_id=channel.id))
        message = Message(
            id=f"msg_{uuid4().hex}",
            user_id=user.id,
            push_key_id=push_key.id,
            source=MessageSource.POST,
            title="retry me",
            content="retry me",
            message_type=MessageType.TEXT,
            requested_channel_ids=[channel.id],
            request_payload={},
            status=MessageStatus.QUEUED,
        )
        session.add(message)
        delivery = Delivery(
            id=str(uuid4()),
            message_id=message.id,
            channel_id=channel.id,
            status=DeliveryStatus.QUEUED,
            adapter_payload={"msgtype": "text", "text": {"content": "retry me"}},
            attempt_logs=[],
        )
        session.add(delivery)
        await session.commit()
        return delivery.id, channel.id


async def test_worker_retries_on_server_error(session_factory, fake_redis) -> None:
    delivery_id, _ = await seed_delivery(session_factory)
    transport = httpx.MockTransport(lambda request: httpx.Response(500, json={"errcode": 500}))
    async with httpx.AsyncClient(transport=transport) as client:
        async with session_factory() as session:
            await process_delivery(session, fake_redis, client, delivery_id)

    async with session_factory() as session:
        delivery = await session.scalar(select(Delivery).where(Delivery.id == delivery_id))
        assert delivery is not None
        assert delivery.status == DeliveryStatus.RETRYING
        assert delivery.attempt_count == 1
        assert delivery.last_response_status == 500
        assert fake_redis.jobs[-1]["kwargs"]["_defer_by"].total_seconds() == 30


async def test_worker_delays_when_channel_rate_limited(session_factory, fake_redis) -> None:
    delivery_id, channel_id = await seed_delivery(session_factory)
    key = f"ratelimit:channel:{channel_id}:{datetime.now(UTC).strftime('%Y%m%d%H%M')}"
    allowed, _, _ = await allow_rate_limit(fake_redis, key, 1)
    assert allowed

    transport = httpx.MockTransport(lambda request: httpx.Response(200, json={"errcode": 0}))
    async with httpx.AsyncClient(transport=transport) as client:
        async with session_factory() as session:
            await process_delivery(session, fake_redis, client, delivery_id)

    async with session_factory() as session:
        delivery = await session.scalar(select(Delivery).where(Delivery.id == delivery_id))
        assert delivery is not None
        assert delivery.status == DeliveryStatus.RETRYING
        assert delivery.attempt_count == 0
        assert fake_redis.jobs[-1]["kwargs"]["_defer_by"].total_seconds() >= 1


async def test_worker_dead_letters_non_retryable_failures(session_factory, fake_redis) -> None:
    delivery_id, _ = await seed_delivery(session_factory)
    transport = httpx.MockTransport(lambda request: httpx.Response(400, json={"errcode": 400}))
    async with httpx.AsyncClient(transport=transport) as client:
        async with session_factory() as session:
            await process_delivery(session, fake_redis, client, delivery_id)

    async with session_factory() as session:
        delivery = await session.scalar(select(Delivery).where(Delivery.id == delivery_id))
        assert delivery is not None
        assert delivery.status == DeliveryStatus.DEAD_LETTER
        assert delivery.dead_lettered_at is not None


async def test_repair_stale_deliveries_requeues_stuck_sending(session_factory, fake_redis) -> None:
    delivery_id, _ = await seed_delivery(session_factory)
    async with session_factory() as session:
        delivery = await session.scalar(select(Delivery).where(Delivery.id == delivery_id))
        assert delivery is not None
        delivery.status = DeliveryStatus.SENDING
        delivery.processing_started_at = datetime.now(UTC).replace(year=2020)
        await session.commit()

    async with session_factory() as session:
        repaired = await repair_stale_deliveries(session, fake_redis)
        assert repaired == 1

    async with session_factory() as session:
        delivery = await session.scalar(select(Delivery).where(Delivery.id == delivery_id))
        assert delivery is not None
        assert delivery.status == DeliveryStatus.QUEUED
        assert delivery.processing_started_at is None
        assert any(job["args"][0] == delivery_id for job in fake_redis.jobs)
