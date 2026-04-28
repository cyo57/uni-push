from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_session
from app.models.user import User
from app.schemas.push_keys import (
    PushKeyCreate,
    PushKeyDeleteResult,
    PushKeyListOut,
    PushKeyOut,
    PushKeyUpdate,
    PushKeyWithSecret,
)
from app.services.audit import record_audit_log
from app.services.push_keys import (
    create_push_key,
    delete_push_key,
    get_push_key_for_user,
    list_push_keys_for_user,
    rotate_push_key,
    update_push_key,
)
from app.services.serializers import push_key_to_out

router = APIRouter(prefix="/push-keys", tags=["push-keys"])


@router.get("", response_model=PushKeyListOut)
async def get_push_keys(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> PushKeyListOut:
    items, total = await list_push_keys_for_user(session, current_user, offset, limit)
    include_channel_secrets = current_user.role.value == "admin"
    return PushKeyListOut(
        items=[
            push_key_to_out(item, include_channel_secrets=include_channel_secrets) for item in items
        ],
        total=total,
    )


@router.post("", response_model=PushKeyWithSecret, status_code=status.HTTP_201_CREATED)
async def post_push_key(
    payload: PushKeyCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> PushKeyWithSecret:
    push_key, plaintext_key = await create_push_key(session, current_user, payload)
    await record_audit_log(
        session,
        actor=current_user,
        action="push_key.create",
        target_type="push_key",
        target_id=push_key.id,
        detail={
            "business_name": push_key.business_name,
            "default_channel_id": push_key.default_channel_id,
            "channel_ids": payload.channel_ids,
        },
    )
    await session.commit()
    return push_key_to_out(
        push_key,
        plaintext_key=plaintext_key,
        include_channel_secrets=current_user.role.value == "admin",
    )


@router.patch("/{push_key_id}", response_model=PushKeyOut)
async def patch_push_key(
    push_key_id: str,
    payload: PushKeyUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> PushKeyOut:
    push_key = await get_push_key_for_user(session, push_key_id, current_user)
    if push_key is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Push key not found")
    updated = await update_push_key(session, push_key, current_user, payload)
    await record_audit_log(
        session,
        actor=current_user,
        action="push_key.update",
        target_type="push_key",
        target_id=updated.id,
        detail=payload.model_dump(exclude_none=True),
    )
    await session.commit()
    return push_key_to_out(updated, include_channel_secrets=current_user.role.value == "admin")


@router.delete("/{push_key_id}", response_model=PushKeyDeleteResult)
async def delete_push_key_route(
    push_key_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> PushKeyDeleteResult:
    push_key = await get_push_key_for_user(session, push_key_id, current_user)
    if push_key is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Push key not found")
    deleted_id = push_key.id
    business_name = push_key.business_name
    await delete_push_key(session, push_key)
    await record_audit_log(
        session,
        actor=current_user,
        action="push_key.delete",
        target_type="push_key",
        target_id=deleted_id,
        detail={"business_name": business_name},
    )
    await session.commit()
    return PushKeyDeleteResult(id=deleted_id)


@router.post("/{push_key_id}/rotate", response_model=PushKeyWithSecret)
async def post_push_key_rotate(
    push_key_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> PushKeyWithSecret:
    push_key = await get_push_key_for_user(session, push_key_id, current_user)
    if push_key is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Push key not found")
    updated, plaintext_key = await rotate_push_key(session, push_key, current_user)
    await record_audit_log(
        session,
        actor=current_user,
        action="push_key.rotate",
        target_type="push_key",
        target_id=updated.id,
        detail={"business_name": updated.business_name},
    )
    await session.commit()
    return push_key_to_out(
        updated,
        plaintext_key=plaintext_key,
        include_channel_secrets=current_user.role.value == "admin",
    )
