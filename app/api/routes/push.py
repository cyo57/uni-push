from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import push_bearer
from app.core.enums import MessageSource
from app.db.session import get_arq_pool, get_session
from app.schemas.messages import PushRequest, PushResponse, PushResponseData
from app.services.messages import enqueue_message
from app.services.push_keys import resolve_push_key_by_token

router = APIRouter(tags=["push"])
MAX_CONTENT_BYTES = 10 * 1024


def _ensure_content_size(content: str) -> None:
    if len(content.encode("utf-8")) > MAX_CONTENT_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE, detail="Content is too large"
        )


async def _resolve_active_push_key(session: AsyncSession, token: str):
    push_key = await resolve_push_key_by_token(session, token)
    if push_key is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid push key")
    if not push_key.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Push key is disabled")
    return push_key


@router.post("/push", response_model=PushResponse)
async def post_push(
    request: Request,
    payload: PushRequest,
    credentials: HTTPAuthorizationCredentials | None = Depends(push_bearer),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key", max_length=128),
    session: AsyncSession = Depends(get_session),
    redis=Depends(get_arq_pool),
) -> PushResponse:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing push key")
    _ensure_content_size(payload.content)
    push_key_model = await _resolve_active_push_key(session, credentials.credentials)
    message_id, deduplicated = await enqueue_message(
        session,
        redis,
        push_key_model,
        MessageSource.POST,
        payload,
        idempotency_key=idempotency_key,
    )
    request.app.state.metrics["push_requests_total"] += 1
    if deduplicated:
        request.app.state.metrics["push_requests_deduplicated_total"] += 1
    return PushResponse(data=PushResponseData(message_id=message_id, deduplicated=deduplicated))
