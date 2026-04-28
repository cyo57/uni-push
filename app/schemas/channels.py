from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import ChannelType, MessageType


class ChannelBase(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    type: ChannelType
    webhook_url: str = Field(min_length=1)
    secret: str | None = Field(default=None, max_length=2048)
    is_enabled: bool = True
    per_minute_limit: int = Field(default=60, ge=1, le=10_000)


class ChannelCreate(ChannelBase):
    pass


class ChannelUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    webhook_url: str | None = Field(default=None, min_length=1)
    secret: str | None = Field(default=None, max_length=2048)
    is_enabled: bool | None = None
    per_minute_limit: int | None = Field(default=None, ge=1, le=10_000)


class ChannelOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    type: ChannelType
    webhook_url: str
    secret: str | None
    has_secret: bool
    secret_preview: str | None
    is_enabled: bool
    is_deleted: bool
    per_minute_limit: int
    created_by_id: str | None
    authorized_group_ids: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class ChannelTestRequest(BaseModel):
    title: str = "UniPush channel test"
    content: str = "This is a test message from UniPush."
    type: MessageType = MessageType.TEXT

class ChannelListOut(BaseModel):
    items: list[ChannelOut]
    total: int
