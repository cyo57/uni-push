from __future__ import annotations

from app.core.crypto import mask_secret
from app.core.enums import DeliveryStatus
from app.models.audit import AuditLog
from app.models.channel import Channel
from app.models.group import UserGroup
from app.models.message import Delivery, Message
from app.models.push_key import PushKey
from app.models.user import User
from app.schemas.audit import AuditLogOut
from app.schemas.auth import CurrentUser
from app.schemas.channels import ChannelOut
from app.schemas.groups import GroupOut
from app.schemas.messages import DeliveryAttemptOut, DeliveryOut, MessageDetailOut, MessageListItem
from app.schemas.push_keys import PushKeyOut, PushKeyWithSecret
from app.schemas.users import UserOut


def user_to_out(user: User) -> UserOut:
    return UserOut(
        id=user.id,
        username=user.username,
        display_name=user.display_name,
        role=user.role,
        is_active=user.is_active,
        group_ids=[membership.group_id for membership in user.group_memberships],
        created_at=user.created_at,
    )


def current_user_to_out(user: User) -> CurrentUser:
    return CurrentUser(
        id=user.id,
        username=user.username,
        display_name=user.display_name,
        role=user.role,
        is_active=user.is_active,
        group_ids=[membership.group_id for membership in user.group_memberships],
        created_at=user.created_at,
    )


def channel_to_out(channel: Channel, include_secrets: bool = False) -> ChannelOut:
    secret_preview = mask_secret(channel.secret) if include_secrets else None
    return ChannelOut(
        id=channel.id,
        name=channel.name,
        type=channel.type,
        webhook_url=channel.webhook_url if include_secrets else "",
        secret=None,
        has_secret=channel.secret is not None,
        secret_preview=secret_preview,
        is_enabled=channel.is_enabled,
        is_deleted=channel.is_deleted,
        per_minute_limit=channel.per_minute_limit,
        created_by_id=channel.created_by_id,
        authorized_user_ids=[permission.user_id for permission in channel.user_permissions],
        authorized_group_ids=[permission.group_id for permission in channel.group_permissions],
        created_at=channel.created_at,
        updated_at=channel.updated_at,
    )


def group_to_out(group: UserGroup) -> GroupOut:
    return GroupOut(
        id=group.id,
        name=group.name,
        description=group.description,
        is_active=group.is_active,
        member_user_ids=[membership.user_id for membership in group.members],
        channel_ids=[permission.channel_id for permission in group.channel_permissions],
        created_at=group.created_at,
        updated_at=group.updated_at,
    )


def audit_log_to_out(entry: AuditLog) -> AuditLogOut:
    return AuditLogOut(
        id=entry.id,
        actor_user_id=entry.actor_user_id,
        actor_username=entry.actor.username if entry.actor is not None else None,
        action=entry.action,
        target_type=entry.target_type,
        target_id=entry.target_id,
        detail=entry.detail,
        created_at=entry.created_at,
    )


def push_key_to_out(
    push_key: PushKey,
    plaintext_key: str | None = None,
    include_channel_secrets: bool = False,
) -> PushKeyOut | PushKeyWithSecret:
    data = PushKeyOut(
        id=push_key.id,
        user_id=push_key.user_id,
        business_name=push_key.business_name,
        key_hint=push_key.key_hint,
        is_active=push_key.is_active,
        per_minute_limit=push_key.per_minute_limit,
        default_channel_id=push_key.default_channel_id,
        channels=[
            channel_to_out(link.channel, include_secrets=include_channel_secrets)
            for link in push_key.channel_links
        ],
        created_at=push_key.created_at,
        updated_at=push_key.updated_at,
        last_rotated_at=push_key.last_rotated_at,
    )
    if plaintext_key is None:
        return data
    return PushKeyWithSecret(**data.model_dump(), plaintext_key=plaintext_key)


def delivery_to_out(delivery: Delivery) -> DeliveryOut:
    return DeliveryOut(
        id=delivery.id,
        channel_id=delivery.channel_id,
        channel_name=delivery.channel.name,
        channel_type=delivery.channel.type.value,
        status=delivery.status,
        attempt_count=delivery.attempt_count,
        processing_started_at=delivery.processing_started_at,
        next_retry_at=delivery.next_retry_at,
        delivered_at=delivery.delivered_at,
        dead_lettered_at=delivery.dead_lettered_at,
        final_error=delivery.final_error,
        last_response_status=delivery.last_response_status,
        last_response_body=delivery.last_response_body,
        adapter_payload=delivery.adapter_payload,
        attempt_logs=[DeliveryAttemptOut.model_validate(item) for item in delivery.attempt_logs],
    )


def message_to_list_item(message: Message) -> MessageListItem:
    success_count = sum(
        1 for delivery in message.deliveries if delivery.status == DeliveryStatus.SUCCESS
    )
    failed_count = sum(
        1
        for delivery in message.deliveries
        if delivery.status in {DeliveryStatus.FAILED, DeliveryStatus.DEAD_LETTER}
    )
    return MessageListItem(
        id=message.id,
        push_key_id=message.push_key_id,
        push_key_business_name=message.push_key.business_name,
        title=message.title,
        message_type=message.message_type,
        status=message.status,
        created_at=message.created_at,
        delivery_count=len(message.deliveries),
        success_count=success_count,
        failed_count=failed_count,
    )


def message_to_detail(message: Message) -> MessageDetailOut:
    return MessageDetailOut(
        id=message.id,
        push_key_id=message.push_key_id,
        push_key_business_name=message.push_key.business_name,
        source=message.source.value,
        title=message.title,
        content=message.content,
        message_type=message.message_type,
        status=message.status,
        requested_channel_ids=message.requested_channel_ids,
        request_payload=message.request_payload,
        created_at=message.created_at,
        deliveries=[delivery_to_out(delivery) for delivery in message.deliveries],
    )
