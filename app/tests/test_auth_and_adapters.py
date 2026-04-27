from app.core.enums import ChannelType, MessageType, UserRole
from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from app.models.channel import Channel
from app.models.user import User
from app.schemas.push_keys import PushKeyCreate
from app.services.adapters import build_adapter_payload
from app.services.push_keys import create_push_key, resolve_push_key_by_token, rotate_push_key


async def test_password_hash_and_jwt_roundtrip() -> None:
    password_hash = hash_password("secret-pass")
    assert verify_password("secret-pass", password_hash)
    token = create_access_token("user-1", UserRole.ADMIN.value)
    payload = decode_access_token(token)
    assert payload["sub"] == "user-1"
    assert payload["role"] == UserRole.ADMIN.value


async def test_adapter_payloads() -> None:
    wecom_markdown = build_adapter_payload(
        ChannelType.WECOM_BOT,
        "Alert",
        "CPU high",
        MessageType.MARKDOWN,
    )
    dingtalk_text = build_adapter_payload(
        ChannelType.DINGTALK_BOT,
        "Alert",
        "CPU high",
        MessageType.TEXT,
    )
    assert wecom_markdown["msgtype"] == "markdown"
    assert "## Alert" in wecom_markdown["markdown"]["content"]
    assert dingtalk_text["msgtype"] == "text"
    assert "Alert" in dingtalk_text["text"]["content"]


async def test_push_key_rotation_invalidates_old_token(session_factory) -> None:
    async with session_factory() as session:
        user = User(
            username="owner",
            display_name="Owner",
            password_hash=hash_password("owner-pass"),
            role=UserRole.ADMIN,
            is_active=True,
        )
        channel = Channel(
            name="Team Ding",
            type=ChannelType.DINGTALK_BOT,
            webhook_url="https://example.test/ding",
            secret="ding-secret",
            is_enabled=True,
            per_minute_limit=60,
        )
        session.add_all([user, channel])
        await session.commit()
        await session.refresh(user)
        await session.refresh(channel)

        push_key, plaintext = await create_push_key(
            session,
            user,
            PushKeyCreate(
                business_name="Ops Alerts",
                per_minute_limit=30,
                channel_ids=[channel.id],
                default_channel_id=channel.id,
            ),
        )

        rotated, new_plaintext = await rotate_push_key(session, push_key, user)
        old_resolved = await resolve_push_key_by_token(session, plaintext)
        new_resolved = await resolve_push_key_by_token(session, new_plaintext)

        assert old_resolved is None
        assert new_resolved is not None
        assert rotated.id == new_resolved.id
