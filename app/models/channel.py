from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import Boolean, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import ChannelType
from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.group import UserGroupChannelPermission
    from app.models.message import Delivery
    from app.models.push_key import PushKey, PushKeyChannel
    from app.models.user import User


class Channel(TimestampMixin, Base):
    __tablename__ = "channels"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    type: Mapped[ChannelType] = mapped_column(Enum(ChannelType, native_enum=False), index=True)
    webhook_url: Mapped[str] = mapped_column(Text)
    secret: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    per_minute_limit: Mapped[int] = mapped_column(Integer, default=60, nullable=False)
    created_by_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    created_by: Mapped[User | None] = relationship(back_populates="created_channels")
    group_permissions: Mapped[list[UserGroupChannelPermission]] = relationship(
        back_populates="channel",
        cascade="all, delete-orphan",
    )
    push_key_links: Mapped[list[PushKeyChannel]] = relationship(back_populates="channel")
    default_for_keys: Mapped[list[PushKey]] = relationship(
        back_populates="default_channel",
        foreign_keys="PushKey.default_channel_id",
    )
    deliveries: Mapped[list[Delivery]] = relationship(back_populates="channel")
