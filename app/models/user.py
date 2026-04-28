from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import Boolean, Enum, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import UserRole
from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.audit import AuditLog
    from app.models.channel import Channel, UserChannelPermission
    from app.models.group import UserGroupMember
    from app.models.message import Message
    from app.models.push_key import PushKey


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(128))
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(Enum(UserRole, native_enum=False), index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    token_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    created_channels: Mapped[list[Channel]] = relationship(back_populates="created_by")
    push_keys: Mapped[list[PushKey]] = relationship(back_populates="user")
    messages: Mapped[list[Message]] = relationship(back_populates="user")
    channel_permissions: Mapped[list[UserChannelPermission]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    group_memberships: Mapped[list[UserGroupMember]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    audit_logs: Mapped[list[AuditLog]] = relationship(back_populates="actor")
