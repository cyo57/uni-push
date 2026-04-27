from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_session
from app.models.user import User
from app.schemas.messages import MessageDetailOut, MessageListOut
from app.services.messages import get_message_detail, get_message_list
from app.services.serializers import message_to_detail, message_to_list_item

router = APIRouter(prefix="/messages", tags=["messages"])


@router.get("", response_model=MessageListOut)
async def get_messages(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> MessageListOut:
    items, total = await get_message_list(session, current_user, offset, limit)
    return MessageListOut(items=[message_to_list_item(item) for item in items], total=total)


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
