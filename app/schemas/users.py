from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import UserRole


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    display_name: str = Field(min_length=1, max_length=128)
    password: str = Field(min_length=8, max_length=128)
    role: UserRole = UserRole.USER
    group_ids: list[str] = Field(default_factory=list)


class UserUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=128)
    password: str | None = Field(default=None, min_length=8, max_length=128)
    role: UserRole | None = None
    is_active: bool | None = None
    group_ids: list[str] | None = None


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    username: str
    display_name: str
    role: UserRole
    is_active: bool
    group_ids: list[str] = Field(default_factory=list)
    created_at: datetime


class UserListOut(BaseModel):
    items: list[UserOut]
    total: int
