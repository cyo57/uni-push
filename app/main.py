from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from time import perf_counter
from uuid import uuid4

import httpx
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import func, select, text

from app.api.router import api_router
from app.core.config import get_settings
from app.core.enums import DeliveryStatus
from app.core.logging import log_event, setup_logging
from app.db.session import create_arq_pool, engine
from app.models.message import Delivery, Message
from app.models.push_key import PushKey

settings = get_settings()
_http_client: httpx.AsyncClient | None = None
_web_dist_dir = Path(__file__).resolve().parent.parent / "web" / "dist"
setup_logging()


def get_http_client() -> httpx.AsyncClient:
    assert _http_client is not None
    return _http_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _http_client
    arq_redis = await create_arq_pool()
    _http_client = httpx.AsyncClient(timeout=settings.http_timeout_seconds)
    app.state.redis = arq_redis
    app.state.arq_redis = arq_redis
    app.state.http_client = _http_client
    try:
        yield
    finally:
        await arq_redis.close()
        await _http_client.aclose()


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.state.metrics = {
    "http_requests_total": 0,
    "http_requests_5xx_total": 0,
    "push_requests_total": 0,
    "push_requests_deduplicated_total": 0,
}
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router, prefix=settings.api_prefix)


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid4()))
    start = perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        duration_ms = round((perf_counter() - start) * 1000, 2)
        app.state.metrics["http_requests_total"] += 1
        app.state.metrics["http_requests_5xx_total"] += 1
        log_event(
            "http_request",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            status_code=500,
            duration_ms=duration_ms,
        )
        raise

    duration_ms = round((perf_counter() - start) * 1000, 2)
    app.state.metrics["http_requests_total"] += 1
    if response.status_code >= 500:
        app.state.metrics["http_requests_5xx_total"] += 1
    response.headers["X-Request-ID"] = request_id
    log_event(
        "http_request",
        request_id=request_id,
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        duration_ms=duration_ms,
    )
    return response


if (_web_dist_dir / "assets").exists():
    app.mount("/assets", StaticFiles(directory=_web_dist_dir / "assets"), name="assets")


async def _check_readiness() -> dict[str, str]:
    async with engine.connect() as connection:
        await connection.execute(text("SELECT 1"))
    await app.state.redis.ping()
    worker_heartbeat = await app.state.redis.get("unipush:worker_heartbeat")
    if worker_heartbeat is None:
        raise RuntimeError("worker heartbeat missing")
    return {"database": "ok", "redis": "ok", "worker": "ok"}


@app.get("/livez")
async def livez() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/readyz")
async def readyz(response: Response) -> dict[str, object]:
    try:
        checks = await _check_readiness()
    except Exception as exc:
        response.status_code = 503
        return {"status": "degraded", "detail": str(exc)}
    return {"status": "ok", "checks": checks}


@app.get("/healthz")
async def healthz(response: Response) -> dict[str, object]:
    return await readyz(response)


@app.get("/metrics", include_in_schema=False)
async def metrics() -> Response:
    async with engine.begin() as connection:
        message_total = int(
            (await connection.scalar(select(func.count()).select_from(Message))) or 0
        )
        active_push_keys = int(
            (
                await connection.scalar(
                    select(func.count()).select_from(PushKey).where(PushKey.is_active.is_(True))
                )
            )
            or 0
        )
        queued_deliveries = int(
            (
                await connection.scalar(
                    select(func.count())
                    .select_from(Delivery)
                    .where(
                        Delivery.status.in_(
                            [
                                DeliveryStatus.QUEUED,
                                DeliveryStatus.RETRYING,
                                DeliveryStatus.SENDING,
                            ]
                        )
                    )
                )
            )
            or 0
        )
        dead_letter_deliveries = int(
            (
                await connection.scalar(
                    select(func.count())
                    .select_from(Delivery)
                    .where(Delivery.status == DeliveryStatus.DEAD_LETTER)
                )
            )
            or 0
        )
    worker_heartbeat = await app.state.redis.get("unipush:worker_heartbeat")
    metrics_payload = "\n".join(
        [
            "# TYPE unipush_http_requests_total counter",
            f"unipush_http_requests_total {app.state.metrics['http_requests_total']}",
            "# TYPE unipush_http_requests_5xx_total counter",
            f"unipush_http_requests_5xx_total {app.state.metrics['http_requests_5xx_total']}",
            "# TYPE unipush_push_requests_total counter",
            f"unipush_push_requests_total {app.state.metrics['push_requests_total']}",
            "# TYPE unipush_push_requests_deduplicated_total counter",
            (
                "unipush_push_requests_deduplicated_total "
                f"{app.state.metrics['push_requests_deduplicated_total']}"
            ),
            "# TYPE unipush_messages_total gauge",
            f"unipush_messages_total {message_total}",
            "# TYPE unipush_active_push_keys gauge",
            f"unipush_active_push_keys {active_push_keys}",
            "# TYPE unipush_deliveries_inflight gauge",
            f"unipush_deliveries_inflight {queued_deliveries}",
            "# TYPE unipush_deliveries_dead_letter_total gauge",
            f"unipush_deliveries_dead_letter_total {dead_letter_deliveries}",
            "# TYPE unipush_worker_heartbeat_up gauge",
            f"unipush_worker_heartbeat_up {1 if worker_heartbeat else 0}",
            "",
        ]
    )
    return Response(content=metrics_payload, media_type="text/plain; version=0.0.4")


@app.get("/", include_in_schema=False)
async def serve_index() -> FileResponse:
    index_file = _web_dist_dir / "index.html"
    if not index_file.exists():
        raise HTTPException(status_code=404, detail="Frontend build not found")
    return FileResponse(index_file)


@app.get("/{full_path:path}", include_in_schema=False)
async def serve_spa(full_path: str) -> FileResponse:
    if full_path.startswith(("api/", "healthz", "livez", "readyz", "metrics")):
        raise HTTPException(status_code=404, detail="Not found")

    requested_file = _web_dist_dir / full_path
    if requested_file.is_file():
        return FileResponse(requested_file)

    index_file = _web_dist_dir / "index.html"
    if not index_file.exists():
        raise HTTPException(status_code=404, detail="Frontend build not found")
    return FileResponse(index_file)


def run() -> None:
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=settings.debug)