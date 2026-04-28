from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.security import create_access_token, hash_password, verify_password
from app.db.session import get_session
from app.models.user import User
from app.schemas.auth import (
    AuthToken,
    CurrentUser,
    CurrentUserUpdate,
    CurrentUserUpdateResult,
    LoginRequest,
)
from app.services.audit import record_audit_log
from app.services.rate_limit import allow_rate_limit
from app.services.serializers import current_user_to_out

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()


async def _enforce_login_rate_limit(request: Request, username: str) -> None:
    redis = getattr(request.app.state, "redis", None)
    if redis is None:
        return

    client_host = request.client.host if request.client else "unknown"
    key = f"ratelimit:login:{client_host}:{username.lower()}"
    allowed, _, ttl = await allow_rate_limit(redis, key, settings.login_rate_limit_per_minute)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many login attempts. Retry in {max(ttl, 1)} seconds.",
        )


@router.post("/login", response_model=AuthToken)
async def login(
    payload: LoginRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> AuthToken:
    await _enforce_login_rate_limit(request, payload.username)
    user = await session.scalar(select(User).where(User.username == payload.username))
    if (
        user is None
        or not user.is_active
        or not verify_password(payload.password, user.password_hash)
    ):
        await record_audit_log(
            session,
            actor=None,
            action="auth.login.failed",
            target_type="auth",
            detail={
                "username": payload.username,
                "client_host": request.client.host if request.client else "unknown",
            },
        )
        await session.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password"
        )
    await record_audit_log(
        session,
        actor=user,
        action="auth.login.success",
        target_type="auth",
        target_id=user.id,
        detail={"client_host": request.client.host if request.client else "unknown"},
    )
    await session.commit()
    return AuthToken(access_token=create_access_token(user.id, user.role.value, user.token_version))


@router.get("/me", response_model=CurrentUser)
async def me(current_user: User = Depends(get_current_user)) -> CurrentUser:
    return current_user_to_out(current_user)


@router.post("/refresh", response_model=AuthToken)
async def refresh_access_token(current_user: User = Depends(get_current_user)) -> AuthToken:
    return AuthToken(
        access_token=create_access_token(
            current_user.id, current_user.role.value, current_user.token_version
        )
    )


@router.patch("/me", response_model=CurrentUserUpdateResult)
async def patch_me(
    payload: CurrentUserUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> CurrentUserUpdateResult:
    rotated_token: str | None = None

    if payload.display_name is not None:
        current_user.display_name = payload.display_name

    if payload.new_password is not None:
        if not payload.current_password or not verify_password(
            payload.current_password, current_user.password_hash
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is invalid",
            )
        current_user.password_hash = hash_password(payload.new_password)
        current_user.token_version += 1
        rotated_token = create_access_token(
            current_user.id, current_user.role.value, current_user.token_version
        )

    changed_fields: list[str] = []
    if payload.display_name is not None:
        changed_fields.append("display_name")
    if payload.new_password is not None:
        changed_fields.append("password")
    if changed_fields:
        await record_audit_log(
            session,
            actor=current_user,
            action="user.self.update",
            target_type="user",
            target_id=current_user.id,
            detail={"fields": changed_fields},
        )
    await session.commit()
    await session.refresh(current_user)
    return CurrentUserUpdateResult(
        user=current_user_to_out(current_user),
        access_token=rotated_token,
        token_type="bearer" if rotated_token else None,
    )
