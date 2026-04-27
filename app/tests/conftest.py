from __future__ import annotations

from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any

import fakeredis.aioredis
import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.deps import get_session
from app.core.enums import UserRole
from app.core.security import create_access_token, hash_password
from app.db.base import Base
from app.main import app
from app.models.user import User


class FakeArqRedis(fakeredis.aioredis.FakeRedis):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, decode_responses=True, **kwargs)
        self.jobs: list[dict[str, Any]] = []

    async def enqueue_job(self, function: str, *args: Any, **kwargs: Any) -> dict[str, Any]:
        job = {"function": function, "args": args, "kwargs": kwargs}
        self.jobs.append(job)
        return job


@pytest.fixture()
async def session_factory(tmp_path: Path) -> AsyncGenerator[async_sessionmaker[AsyncSession]]:
    db_path = tmp_path / "test.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield factory
    await engine.dispose()


@pytest.fixture()
async def fake_redis() -> AsyncGenerator[FakeArqRedis]:
    redis = FakeArqRedis()
    yield redis
    await redis.aclose()


@pytest.fixture()
async def client(
    session_factory: async_sessionmaker[AsyncSession],
    fake_redis: FakeArqRedis,
) -> AsyncGenerator[httpx.AsyncClient]:
    async def override_get_session() -> AsyncGenerator[AsyncSession]:
        async with session_factory() as session:
            yield session

    transport = httpx.MockTransport(lambda request: httpx.Response(200, json={"errcode": 0}))
    app.dependency_overrides[get_session] = override_get_session
    app.state.redis = fake_redis
    app.state.arq_redis = fake_redis
    app.state.http_client = httpx.AsyncClient(transport=transport)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as api:
        yield api
    await app.state.http_client.aclose()
    app.dependency_overrides.clear()


@pytest.fixture()
async def admin_user(session_factory: async_sessionmaker[AsyncSession]) -> User:
    async with session_factory() as session:
        user = User(
            username="admin",
            display_name="Admin",
            password_hash=hash_password("admin-pass"),
            role=UserRole.ADMIN,
            is_active=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


@pytest.fixture()
async def normal_user(session_factory: async_sessionmaker[AsyncSession]) -> User:
    async with session_factory() as session:
        user = User(
            username="user",
            display_name="User",
            password_hash=hash_password("user-pass"),
            role=UserRole.USER,
            is_active=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


@pytest.fixture()
def admin_headers(admin_user: User) -> dict[str, str]:
    token = create_access_token(admin_user.id, admin_user.role.value)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def user_headers(normal_user: User) -> dict[str, str]:
    token = create_access_token(normal_user.id, normal_user.role.value)
    return {"Authorization": f"Bearer {token}"}
