from datetime import datetime

from pydantic import BaseModel, Field


class AuditLogOut(BaseModel):
    id: str
    actor_user_id: str | None
    actor_username: str | None
    action: str
    target_type: str
    target_id: str | None
    detail: dict = Field(default_factory=dict)
    created_at: datetime


class AuditLogListOut(BaseModel):
    items: list[AuditLogOut]
    total: int
