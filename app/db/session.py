from __future__ import annotations

from collections.abc import AsyncGenerator

from arq.connections import ArqRedis, RedisSettings, create_pool
from fastapi import Request
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings

settings = get_settings()

engine: AsyncEngine = create_async_engine(settings.database_url, future=True)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_session() -> AsyncGenerator[AsyncSession]:
    async with AsyncSessionLocal() as session:
        yield session


def get_redis_client(request: Request) -> Redis:
    return request.app.state.redis


def get_arq_pool(request: Request) -> ArqRedis:
    return request.app.state.arq_redis


async def create_arq_pool() -> ArqRedis:
    return await create_pool(RedisSettings.from_dsn(settings.redis_url))
