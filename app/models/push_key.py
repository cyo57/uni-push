from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.channel import Channel
    from app.models.message import Message
    from app.models.user import User


class PushKeyChannel(TimestampMixin, Base):
    __tablename__ = "push_key_channels"

    push_key_id: Mapped[str] = mapped_column(
        ForeignKey("push_keys.id", ondelete="CASCADE"),
        primary_key=True,
    )
    channel_id: Mapped[str] = mapped_column(
        ForeignKey("channels.id", ondelete="CASCADE"),
        primary_key=True,
    )

    push_key: Mapped[PushKey] = relationship(back_populates="channel_links")
    channel: Mapped[Channel] = relationship(back_populates="push_key_links")


class PushKey(TimestampMixin, Base):
    __tablename__ = "push_keys"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    business_name: Mapped[str] = mapped_column(String(128), index=True)
    key_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    key_hint: Mapped[str] = mapped_column(String(32))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    per_minute_limit: Mapped[int] = mapped_column(Integer, default=60, nullable=False)
    default_channel_id: Mapped[str] = mapped_column(ForeignKey("channels.id"), index=True)
    last_rotated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    user: Mapped[User] = relationship(back_populates="push_keys")
    default_channel: Mapped[Channel] = relationship(
        back_populates="default_for_keys",
        foreign_keys=[default_channel_id],
    )
    channel_links: Mapped[list[PushKeyChannel]] = relationship(
        back_populates="push_key",
        cascade="all, delete-orphan",
    )
    messages: Mapped[list[Message]] = relationship(back_populates="push_key")
