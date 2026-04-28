from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin
from app.db.session import get_session
from app.models.channel import Channel
from app.models.user import User
from app.schemas.groups import GroupCreate, GroupListOut, GroupOut, GroupUpdate
from app.services.audit import record_audit_log
from app.services.groups import (
    create_group,
    delete_group,
    get_group_by_id,
    list_groups,
    set_group_channel_permission,
    set_group_member,
    update_group,
)
from app.services.serializers import group_to_out

router = APIRouter(prefix="/groups", tags=["groups"])


@router.get("", response_model=GroupListOut)
async def get_groups(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    _: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> GroupListOut:
    items, total = await list_groups(session, offset, limit)
    return GroupListOut(items=[group_to_out(item) for item in items], total=total)


@router.post("", response_model=GroupOut, status_code=status.HTTP_201_CREATED)
async def post_group(
    payload: GroupCreate,
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> GroupOut:
    try:
        group = await create_group(session, payload)
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Group name already exists",
        ) from exc
    await record_audit_log(
        session,
        actor=current_user,
        action="group.create",
        target_type="group",
        target_id=group.id,
        detail={"name": group.name},
    )
    await session.commit()
    return group_to_out(group)


@router.patch("/{group_id}", response_model=GroupOut)
async def patch_group(
    group_id: str,
    payload: GroupUpdate,
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> GroupOut:
    group = await get_group_by_id(session, group_id)
    if group is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")
    try:
        updated = await update_group(session, group, payload)
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Group name already exists",
        ) from exc
    await record_audit_log(
        session,
        actor=current_user,
        action="group.update",
        target_type="group",
        target_id=updated.id,
        detail=payload.model_dump(exclude_none=True),
    )
    await session.commit()
    return group_to_out(updated)


@router.delete("/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_group_route(
    group_id: str,
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> None:
    group = await get_group_by_id(session, group_id)
    if group is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")
    group_name = group.name
    await delete_group(session, group)
    await record_audit_log(
        session,
        actor=current_user,
        action="group.delete",
        target_type="group",
        target_id=group_id,
        detail={"name": group_name},
    )
    await session.commit()


@router.post("/{group_id}/members/{user_id}", response_model=GroupOut)
async def grant_group_member(
    group_id: str,
    user_id: str,
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> GroupOut:
    group = await get_group_by_id(session, group_id)
    user = await session.scalar(select(User).where(User.id == user_id))
    if group is None or user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group or user not found")
    updated = await set_group_member(session, group, user_id, granted=True)
    await record_audit_log(
        session,
        actor=current_user,
        action="group.member.grant",
        target_type="group",
        target_id=updated.id,
        detail={"user_id": user_id},
    )
    await session.commit()
    return group_to_out(updated)


@router.delete("/{group_id}/members/{user_id}", response_model=GroupOut)
async def revoke_group_member(
    group_id: str,
    user_id: str,
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> GroupOut:
    group = await get_group_by_id(session, group_id)
    user = await session.scalar(select(User).where(User.id == user_id))
    if group is None or user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group or user not found")
    updated = await set_group_member(session, group, user_id, granted=False)
    await record_audit_log(
        session,
        actor=current_user,
        action="group.member.revoke",
        target_type="group",
        target_id=updated.id,
        detail={"user_id": user_id},
    )
    await session.commit()
    return group_to_out(updated)


@router.post("/{group_id}/channels/{channel_id}", response_model=GroupOut)
async def grant_group_channel_permission(
    group_id: str,
    channel_id: str,
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> GroupOut:
    group = await get_group_by_id(session, group_id)
    channel = await session.scalar(
        select(Channel).where(Channel.id == channel_id, Channel.is_deleted.is_(False))
    )
    if group is None or channel is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group or channel not found",
        )
    updated = await set_group_channel_permission(session, group, channel_id, granted=True)
    await record_audit_log(
        session,
        actor=current_user,
        action="group.channel.grant",
        target_type="group",
        target_id=updated.id,
        detail={"channel_id": channel_id},
    )
    await session.commit()
    return group_to_out(updated)


@router.delete("/{group_id}/channels/{channel_id}", response_model=GroupOut)
async def revoke_group_channel_permission(
    group_id: str,
    channel_id: str,
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> GroupOut:
    group = await get_group_by_id(session, group_id)
    channel = await session.scalar(
        select(Channel).where(Channel.id == channel_id, Channel.is_deleted.is_(False))
    )
    if group is None or channel is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group or channel not found",
        )
    updated = await set_group_channel_permission(session, group, channel_id, granted=False)
    await record_audit_log(
        session,
        actor=current_user,
        action="group.channel.revoke",
        target_type="group",
        target_id=updated.id,
        detail={"channel_id": channel_id},
    )
    await session.commit()
    return group_to_out(updated)
