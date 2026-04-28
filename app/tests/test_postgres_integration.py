from __future__ import annotations

import os
from collections.abc import AsyncGenerator

import fakeredis.aioredis
import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.deps import get_session
from app.core.enums import (
    ChannelType,
    DeliveryStatus,
    MessageSource,
    MessageStatus,
    MessageType,
    UserRole,
)
from app.core.security import create_access_token, hash_password
from app.db.base import Base
from app.main import app
from app.models.channel import Channel
from app.models.message import Delivery, Message
from app.models.push_key import PushKey, PushKeyChannel
from app.models.user import User

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not TEST_DATABASE_URL,
    reason="TEST_DATABASE_URL is not configured",
)


@pytest.fixture()
async def postgres_session_factory() -> AsyncGenerator[async_sessionmaker[AsyncSession]]:
    assert TEST_DATABASE_URL
    engine = create_async_engine(TEST_DATABASE_URL)
    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield factory
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture()
async def postgres_client(
    postgres_session_factory: async_sessionmaker[AsyncSession],
) -> AsyncGenerator[httpx.AsyncClient]:
    async def override_get_session() -> AsyncGenerator[AsyncSession]:
        async with postgres_session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    app.state.redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client
    await app.state.redis.aclose()
    app.dependency_overrides.clear()


async def test_postgres_dashboard_requests_and_export(
    postgres_session_factory: async_sessionmaker[AsyncSession],
    postgres_client: httpx.AsyncClient,
) -> None:
    async with postgres_session_factory() as session:
        user = User(
            username="pg-admin",
            display_name="PG Admin",
            password_hash=hash_password("pg-admin-pass"),
            role=UserRole.ADMIN,
            is_active=True,
        )
        channel = Channel(
            name="pg-channel",
            type=ChannelType.GENERIC_WEBHOOK,
            webhook_url="https://example.test/pg",
            is_enabled=True,
            per_minute_limit=20,
        )
        session.add_all([user, channel])
        await session.flush()

        push_key = PushKey(
            user_id=user.id,
            business_name="pg-key",
            key_hash="pg-hash",
            key_hint="pg...",
            is_active=True,
            per_minute_limit=20,
            default_channel_id=channel.id,
        )
        session.add(push_key)
        await session.flush()
        session.add(PushKeyChannel(push_key_id=push_key.id, channel_id=channel.id))

        message = Message(
            id="msg_pg_seed",
            user_id=user.id,
            push_key_id=push_key.id,
            source=MessageSource.POST,
            title="postgres export",
            content="body",
            message_type=MessageType.TEXT,
            requested_channel_ids=[channel.id],
            request_payload={"title": "postgres export"},
            status=MessageStatus.SUCCESS,
        )
        session.add(message)
        session.add(
            Delivery(
                id="delivery_pg_seed",
                message_id=message.id,
                channel_id=channel.id,
                status=DeliveryStatus.SUCCESS,
                adapter_payload={"title": "postgres export"},
                attempt_logs=[],
            )
        )
        await session.commit()
        token = create_access_token(user.id, user.role.value, user.token_version)

    headers = {"Authorization": f"Bearer {token}"}
    dashboard = await postgres_client.get("/api/v1/dashboard/requests", headers=headers)
    exported = await postgres_client.get("/api/v1/messages/export", headers=headers)

    assert dashboard.status_code == 200
    assert any(point["value"] >= 1 for point in dashboard.json())
    assert exported.status_code == 200
    assert "postgres export" in exported.text
