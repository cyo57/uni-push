from __future__ import annotations

import httpx
from arq import cron
from arq.connections import RedisSettings

from app.core.config import get_settings
from app.db.session import AsyncSessionLocal
from app.services.messages import cleanup_expired_messages, process_delivery

settings = get_settings()


async def worker_startup(ctx: dict) -> None:
    ctx["http_client"] = httpx.AsyncClient(timeout=settings.http_timeout_seconds)


async def worker_shutdown(ctx: dict) -> None:
    await ctx["http_client"].aclose()


async def deliver_message(ctx: dict, delivery_id: str) -> None:
    async with AsyncSessionLocal() as session:
        await process_delivery(session, ctx["redis"], ctx["http_client"], delivery_id)


async def cleanup_logs(ctx: dict) -> int:
    async with AsyncSessionLocal() as session:
        return await cleanup_expired_messages(session)


class WorkerSettings:
    functions = [deliver_message]
    cron_jobs = [cron(cleanup_logs, hour={0, 6, 12, 18}, minute={5})]
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    on_startup = worker_startup
    on_shutdown = worker_shutdown
