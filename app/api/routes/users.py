from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import UserRole
from app.api.deps import require_admin
from app.db.session import get_session
from app.models.user import User
from app.schemas.users import UserCreate, UserListOut, UserOut, UserUpdate
from app.services.audit import record_audit_log
from app.services.serializers import user_to_out
from app.services.users import create_user, list_users, update_user

router = APIRouter(prefix="/users", tags=["users"])


def _parse_csv_values(value: str | None) -> list[str] | None:
    if not value:
        return None
    items = [item.strip() for item in value.split(",") if item.strip()]
    return list(dict.fromkeys(items)) or None


def _parse_role_filters(value: str | None) -> list[str] | None:
    values = _parse_csv_values(value)
    if not values:
        return None
    parsed: list[str] = []
    for item in values:
        try:
            parsed.append(UserRole(item).value)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid role filter: {item}",
            ) from exc
    return parsed


def _parse_status_filters(value: str | None) -> list[bool] | None:
    values = _parse_csv_values(value)
    if not values:
        return None
    mapping = {"active": True, "inactive": False}
    try:
        return list(dict.fromkeys(mapping[item] for item in values))
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid status filter: {exc.args[0]}",
        ) from exc


@router.get("", response_model=UserListOut)
async def get_users(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    q: str | None = Query(default=None, min_length=1, max_length=128),
    roles: str | None = Query(default=None, max_length=128),
    statuses: str | None = Query(default=None, max_length=128),
    group_ids: str | None = Query(default=None, max_length=2048),
    _: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> UserListOut:
    items, total = await list_users(
        session,
        offset,
        limit,
        q=q,
        roles=_parse_role_filters(roles),
        statuses=_parse_status_filters(statuses),
        group_ids=_parse_csv_values(group_ids),
    )
    return UserListOut(items=[user_to_out(item) for item in items], total=total)


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def post_user(
    payload: UserCreate,
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> UserOut:
    try:
        user = await create_user(session, payload)
    except ValueError as exc:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Username already exists"
        ) from exc
    await record_audit_log(
        session,
        actor=current_user,
        action="user.create",
        target_type="user",
        target_id=user.id,
        detail={"username": user.username, "role": user.role.value},
    )
    await session.commit()
    return user_to_out(user)


@router.patch("/{user_id}", response_model=UserOut)
async def patch_user(
    user_id: str,
    payload: UserUpdate,
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> UserOut:
    user = await session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    try:
        updated = await update_user(session, user, payload)
    except ValueError as exc:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Username conflict"
        ) from exc
    await record_audit_log(
        session,
        actor=current_user,
        action="user.update",
        target_type="user",
        target_id=updated.id,
        detail=payload.model_dump(exclude_none=True),
    )
    await session.commit()
    return user_to_out(updated)
