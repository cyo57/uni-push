from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.security import create_access_token, verify_password
from app.db.session import get_session
from app.models.user import User
from app.schemas.auth import AuthToken, CurrentUser, LoginRequest
from app.services.serializers import current_user_to_out

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=AuthToken)
async def login(payload: LoginRequest, session: AsyncSession = Depends(get_session)) -> AuthToken:
    user = await session.scalar(select(User).where(User.username == payload.username))
    if (
        user is None
        or not user.is_active
        or not verify_password(payload.password, user.password_hash)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password"
        )
    return AuthToken(access_token=create_access_token(user.id, user.role.value))


@router.get("/me", response_model=CurrentUser)
async def me(current_user: User = Depends(get_current_user)) -> CurrentUser:
    return current_user_to_out(current_user)
