from datetime import datetime

from pydantic import BaseModel, Field


class GroupCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    description: str | None = Field(default=None, max_length=1024)
    is_active: bool = True


class GroupUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    description: str | None = Field(default=None, max_length=1024)
    is_active: bool | None = None


class GroupOut(BaseModel):
    id: str
    name: str
    description: str | None
    is_active: bool
    member_user_ids: list[str] = Field(default_factory=list)
    channel_ids: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class GroupListOut(BaseModel):
    items: list[GroupOut]
    total: int
