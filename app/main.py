from __future__ import annotations

from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import get_settings
from app.db.session import create_arq_pool

settings = get_settings()
_http_client: httpx.AsyncClient | None = None


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
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router, prefix=settings.api_prefix)


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


def run() -> None:
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=settings.debug)
