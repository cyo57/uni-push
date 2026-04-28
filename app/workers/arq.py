from __future__ import annotations

import httpx
from arq import cron
from arq.connections import RedisSettings

from app.core.config import get_settings
from app.core.logging import log_event, setup_logging
from app.db.session import AsyncSessionLocal
from app.services.messages import (
    cleanup_expired_messages,
    process_delivery,
    repair_stale_deliveries,
)

settings = get_settings()
setup_logging()


async def worker_startup(ctx: dict) -> None:
    ctx["http_client"] = httpx.AsyncClient(timeout=settings.http_timeout_seconds)
    await ctx["redis"].set(
        "unipush:worker_heartbeat",
        "ok",
        ex=settings.worker_heartbeat_ttl_seconds,
    )
    log_event("worker_startup")


async def worker_shutdown(ctx: dict) -> None:
    await ctx["http_client"].aclose()
    log_event("worker_shutdown")


async def deliver_message(ctx: dict, delivery_id: str) -> None:
    await ctx["redis"].set(
        "unipush:worker_heartbeat",
        "ok",
        ex=settings.worker_heartbeat_ttl_seconds,
    )
    async with AsyncSessionLocal() as session:
        await process_delivery(session, ctx["redis"], ctx["http_client"], delivery_id)


async def cleanup_logs(ctx: dict) -> int:
    async with AsyncSessionLocal() as session:
        deleted = await cleanup_expired_messages(session)
    log_event("cleanup_logs", deleted=deleted)
    return deleted


async def refresh_worker_heartbeat(ctx: dict) -> int:
    await ctx["redis"].set(
        "unipush:worker_heartbeat",
        "ok",
        ex=settings.worker_heartbeat_ttl_seconds,
    )
    return 1


async def requeue_stale_deliveries(ctx: dict) -> int:
    async with AsyncSessionLocal() as session:
        repaired = await repair_stale_deliveries(session, ctx["redis"])
    log_event("requeue_stale_deliveries", repaired=repaired)
    return repaired


class WorkerSettings:
    functions = [deliver_message]
    cron_jobs = [
        cron(cleanup_logs, hour={0, 6, 12, 18}, minute={5}),
        cron(refresh_worker_heartbeat, minute=set(range(60))),
        cron(requeue_stale_deliveries, minute={1, 11, 21, 31, 41, 51}),
    ]
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    on_startup = worker_startup
    on_shutdown = worker_shutdown
