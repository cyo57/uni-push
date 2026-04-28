from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.channel import Channel
    from app.models.user import User


class UserGroupMember(TimestampMixin, Base):
    __tablename__ = "user_group_members"

    group_id: Mapped[str] = mapped_column(
        ForeignKey("user_groups.id", ondelete="CASCADE"),
        primary_key=True,
    )
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )

    group: Mapped[UserGroup] = relationship(back_populates="members")
    user: Mapped[User] = relationship(back_populates="group_memberships")


class UserGroupChannelPermission(TimestampMixin, Base):
    __tablename__ = "user_group_channel_permissions"

    group_id: Mapped[str] = mapped_column(
        ForeignKey("user_groups.id", ondelete="CASCADE"),
        primary_key=True,
    )
    channel_id: Mapped[str] = mapped_column(
        ForeignKey("channels.id", ondelete="CASCADE"),
        primary_key=True,
    )

    group: Mapped[UserGroup] = relationship(back_populates="channel_permissions")
    channel: Mapped[Channel] = relationship(back_populates="group_permissions")


class UserGroup(TimestampMixin, Base):
    __tablename__ = "user_groups"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    members: Mapped[list[UserGroupMember]] = relationship(
        back_populates="group",
        cascade="all, delete-orphan",
    )
    channel_permissions: Mapped[list[UserGroupChannelPermission]] = relationship(
        back_populates="group",
        cascade="all, delete-orphan",
    )
