from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import push_bearer
from app.core.enums import MessageSource, MessageType
from app.db.session import get_arq_pool, get_session
from app.schemas.messages import PushRequest, PushResponse, PushResponseData
from app.services.messages import enqueue_message
from app.services.push_keys import resolve_push_key_by_token

router = APIRouter(tags=["push"])


async def _resolve_active_push_key(session: AsyncSession, token: str):
    push_key = await resolve_push_key_by_token(session, token)
    if push_key is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid push key")
    if not push_key.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Push key is disabled")
    return push_key


@router.get("/send/{push_key}", response_model=PushResponse)
async def get_send(
    push_key: str = Path(),
    title: str = Query(min_length=1, max_length=255),
    content: str = Query(min_length=1),
    type: MessageType = Query(default=MessageType.TEXT),
    session: AsyncSession = Depends(get_session),
    redis=Depends(get_arq_pool),
) -> PushResponse:
    if len(content.encode("utf-8")) > 10 * 1024:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Content is too large"
        )
    push_key_model = await _resolve_active_push_key(session, push_key)
    message_id = await enqueue_message(
        session,
        redis,
        push_key_model,
        MessageSource.GET,
        PushRequest(title=title, content=content, type=type, channel_ids=None),
    )
    return PushResponse(data=PushResponseData(message_id=message_id))


@router.post("/push", response_model=PushResponse)
async def post_push(
    payload: PushRequest,
    credentials: HTTPAuthorizationCredentials | None = Depends(push_bearer),
    session: AsyncSession = Depends(get_session),
    redis=Depends(get_arq_pool),
) -> PushResponse:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing push key")
    push_key_model = await _resolve_active_push_key(session, credentials.credentials)
    message_id = await enqueue_message(session, redis, push_key_model, MessageSource.POST, payload)
    return PushResponse(data=PushResponseData(message_id=message_id))
