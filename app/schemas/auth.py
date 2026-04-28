from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import UserRole


class LoginRequest(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=1, max_length=128)


class AuthToken(BaseModel):
    access_token: str
    token_type: str = "bearer"


class CurrentUser(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    username: str
    display_name: str
    role: UserRole
    is_active: bool
    group_ids: list[str] = Field(default_factory=list)
    created_at: datetime


class CurrentUserUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=128)
    current_password: str | None = None
    new_password: str | None = Field(default=None, min_length=8, max_length=128)


class CurrentUserUpdateResult(BaseModel):
    user: CurrentUser
    access_token: str | None = None
    token_type: str | None = None
