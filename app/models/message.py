from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import DeliveryStatus, MessageSource, MessageStatus, MessageType
from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.channel import Channel
    from app.models.push_key import PushKey
    from app.models.user import User


class Message(TimestampMixin, Base):
    __tablename__ = "messages"
    __table_args__ = (
        UniqueConstraint(
            "push_key_id",
            "idempotency_key",
            name="uq_messages_push_key_idempotency_key",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    push_key_id: Mapped[str] = mapped_column(
        ForeignKey("push_keys.id", ondelete="CASCADE"), index=True
    )
    source: Mapped[MessageSource] = mapped_column(Enum(MessageSource, native_enum=False))
    title: Mapped[str] = mapped_column(String(255))
    content: Mapped[str] = mapped_column(Text)
    message_type: Mapped[MessageType] = mapped_column(Enum(MessageType, native_enum=False))
    requested_channel_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    request_payload: Mapped[dict] = mapped_column(JSON, default=dict)
    idempotency_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    idempotency_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[MessageStatus] = mapped_column(
        Enum(MessageStatus, native_enum=False),
        default=MessageStatus.QUEUED,
        nullable=False,
        index=True,
    )

    user: Mapped[User] = relationship(back_populates="messages")
    push_key: Mapped[PushKey] = relationship(back_populates="messages")
    deliveries: Mapped[list[Delivery]] = relationship(
        back_populates="message",
        cascade="all, delete-orphan",
    )


class Delivery(TimestampMixin, Base):
    __tablename__ = "deliveries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    message_id: Mapped[str] = mapped_column(
        ForeignKey("messages.id", ondelete="CASCADE"), index=True
    )
    channel_id: Mapped[str] = mapped_column(
        ForeignKey("channels.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[DeliveryStatus] = mapped_column(
        Enum(DeliveryStatus, native_enum=False),
        default=DeliveryStatus.PENDING,
        nullable=False,
        index=True,
    )
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    next_retry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    processing_started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    dead_lettered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    final_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    adapter_payload: Mapped[dict] = mapped_column(JSON, default=dict)
    attempt_logs: Mapped[list[dict]] = mapped_column(JSON, default=list)
    last_response_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_response_body: Mapped[str | None] = mapped_column(Text, nullable=True)

    message: Mapped[Message] = relationship(back_populates="deliveries")
    channel: Mapped[Channel] = relationship(back_populates="deliveries")
