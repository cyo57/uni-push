from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.channels import ChannelOut


class PushKeyCreate(BaseModel):
    business_name: str = Field(min_length=1, max_length=128)
    per_minute_limit: int = Field(default=60, ge=1, le=10_000)
    channel_ids: list[str] = Field(min_length=1)
    default_channel_id: str


class PushKeyUpdate(BaseModel):
    business_name: str | None = Field(default=None, min_length=1, max_length=128)
    per_minute_limit: int | None = Field(default=None, ge=1, le=10_000)
    channel_ids: list[str] | None = Field(default=None, min_length=1)
    default_channel_id: str | None = None
    is_active: bool | None = None


class PushKeyOut(BaseModel):
    id: str
    user_id: str
    business_name: str
    key_hint: str
    is_active: bool
    per_minute_limit: int
    default_channel_id: str
    channels: list[ChannelOut]
    created_at: datetime
    updated_at: datetime
    last_rotated_at: datetime


class PushKeyWithSecret(PushKeyOut):
    plaintext_key: str


class PushKeyListOut(BaseModel):
    items: list[PushKeyOut]
    total: int


class PushKeyDeleteResult(BaseModel):
    id: str
