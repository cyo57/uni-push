from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_admin
from app.db.session import get_session
from app.models.user import User
from app.schemas.channels import (
    ChannelCreate,
    ChannelListOut,
    ChannelOut,
    ChannelTestRequest,
    ChannelUpdate,
)
from app.services.audit import record_audit_log
from app.services.channels import (
    create_channel,
    get_channel_by_id,
    list_channels_for_user,
    set_channel_permission,
    soft_delete_channel,
    update_channel,
)
from app.services.messages import test_channel
from app.services.serializers import channel_to_out

router = APIRouter(prefix="/channels", tags=["channels"])


@router.get("", response_model=ChannelListOut)
async def get_channels(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ChannelListOut:
    items, total = await list_channels_for_user(session, current_user, offset, limit)
    include_secrets = current_user.role.value == "admin"
    return ChannelListOut(
        items=[channel_to_out(item, include_secrets=include_secrets) for item in items],
        total=total,
    )


@router.post("", response_model=ChannelOut, status_code=status.HTTP_201_CREATED)
async def post_channel(
    payload: ChannelCreate,
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> ChannelOut:
    try:
        channel = await create_channel(session, current_user, payload)
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Channel name already exists"
        ) from exc
    await record_audit_log(
        session,
        actor=current_user,
        action="channel.create",
        target_type="channel",
        target_id=channel.id,
        detail={"name": channel.name, "type": channel.type.value},
    )
    await session.commit()
    return channel_to_out(channel, include_secrets=True)


@router.patch("/{channel_id}", response_model=ChannelOut)
async def patch_channel(
    channel_id: str,
    payload: ChannelUpdate,
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> ChannelOut:
    channel = await get_channel_by_id(session, channel_id)
    if channel is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Channel not found")
    try:
        updated = await update_channel(session, channel, payload)
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Channel name already exists"
        ) from exc
    await record_audit_log(
        session,
        actor=current_user,
        action="channel.update",
        target_type="channel",
        target_id=updated.id,
        detail=payload.model_dump(exclude_none=True),
    )
    await session.commit()
    return channel_to_out(updated, include_secrets=True)


@router.delete("/{channel_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_channel(
    channel_id: str,
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> None:
    channel = await get_channel_by_id(session, channel_id)
    if channel is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Channel not found")
    await soft_delete_channel(session, channel)
    await record_audit_log(
        session,
        actor=current_user,
        action="channel.delete",
        target_type="channel",
        target_id=channel.id,
        detail={"name": channel.name},
    )
    await session.commit()


@router.post("/{channel_id}/test")
async def post_channel_test(
    channel_id: str,
    payload: ChannelTestRequest,
    request: Request,
    _: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> dict:
    channel = await get_channel_by_id(session, channel_id)
    if channel is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Channel not found")
    result = await test_channel(channel, payload, request.app.state.http_client)
    return {
        "success": result.success,
        "retryable": result.retryable,
        "status_code": result.status_code,
        "response_body": result.response_body,
        "error": result.error,
    }


@router.post("/{channel_id}/permissions/{user_id}", response_model=ChannelOut)
async def grant_channel_permission(
    channel_id: str,
    user_id: str,
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> ChannelOut:
    channel = await get_channel_by_id(session, channel_id)
    user = await session.scalar(select(User).where(User.id == user_id))
    if channel is None or user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Channel or user not found"
        )
    updated = await set_channel_permission(session, channel, user_id, granted=True)
    await record_audit_log(
        session,
        actor=current_user,
        action="channel.permission.grant",
        target_type="channel",
        target_id=updated.id,
        detail={"user_id": user_id},
    )
    await session.commit()
    return channel_to_out(updated, include_secrets=True)


@router.delete("/{channel_id}/permissions/{user_id}", response_model=ChannelOut)
async def revoke_channel_permission(
    channel_id: str,
    user_id: str,
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> ChannelOut:
    channel = await get_channel_by_id(session, channel_id)
    user = await session.scalar(select(User).where(User.id == user_id))
    if channel is None or user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Channel or user not found"
        )
    updated = await set_channel_permission(session, channel, user_id, granted=False)
    await record_audit_log(
        session,
        actor=current_user,
        action="channel.permission.revoke",
        target_type="channel",
        target_id=updated.id,
        detail={"user_id": user_id},
    )
    await session.commit()
    return channel_to_out(updated, include_secrets=True)
