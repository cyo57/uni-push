from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.enums import MessageStatus
from app.db.session import get_arq_pool, get_session
from app.models.user import User
from app.schemas.messages import MessageDetailOut, MessageListOut, MessageReplayResponse
from app.services.audit import record_audit_log
from app.services.messages import (
    get_message_detail,
    get_message_list,
    replay_message,
    retry_failed_delivery,
    stream_messages_csv,
)
from app.services.serializers import message_to_detail, message_to_list_item

router = APIRouter(prefix="/messages", tags=["messages"])


@router.get("", response_model=MessageListOut)
async def get_messages(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    q: str | None = Query(default=None, min_length=1, max_length=128),
    status_filter: MessageStatus | None = Query(default=None, alias="status"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> MessageListOut:
    items, total = await get_message_list(
        session,
        current_user,
        offset,
        limit,
        q=q,
        status_filter=status_filter,
    )
    return MessageListOut(items=[message_to_list_item(item) for item in items], total=total)


@router.get("/export")
async def export_messages(
    q: str | None = Query(default=None, min_length=1, max_length=128),
    status_filter: MessageStatus | None = Query(default=None, alias="status"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> StreamingResponse:
    return StreamingResponse(
        stream_messages_csv(session, current_user, q=q, status_filter=status_filter),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="messages.csv"'},
    )


@router.get("/{message_id}", response_model=MessageDetailOut)
async def get_message(
    message_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> MessageDetailOut:
    message = await get_message_detail(session, current_user, message_id)
    if message is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")
    return message_to_detail(message)


@router.post("/{message_id}/replay", response_model=MessageReplayResponse)
async def post_replay_message(
    message_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    redis=Depends(get_arq_pool),
) -> MessageReplayResponse:
    new_message_id = await replay_message(session, redis, current_user, message_id)
    await record_audit_log(
        session,
        actor=current_user,
        action="message.replay",
        target_type="message",
        target_id=message_id,
        detail={"new_message_id": new_message_id},
    )
    await session.commit()
    return MessageReplayResponse(message_id=new_message_id)


@router.post("/{message_id}/deliveries/{delivery_id}/retry", status_code=status.HTTP_204_NO_CONTENT)
async def post_retry_delivery(
    message_id: str,
    delivery_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    redis=Depends(get_arq_pool),
) -> None:
    await retry_failed_delivery(session, redis, current_user, message_id, delivery_id)
    await record_audit_log(
        session,
        actor=current_user,
        action="delivery.retry",
        target_type="delivery",
        target_id=delivery_id,
        detail={"message_id": message_id},
    )
    await session.commit()
