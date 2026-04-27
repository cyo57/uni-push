from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.core.enums import UserRole


class LoginRequest(BaseModel):
    username: str
    password: str


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
    created_at: datetime
