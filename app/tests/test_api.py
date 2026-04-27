from sqlalchemy import select

from app.core.enums import ChannelType, DeliveryStatus, MessageType
from app.models.message import Delivery, Message


async def create_channel_via_api(client, admin_headers, name: str, type_: str) -> dict:
    response = await client.post(
        "/api/v1/channels",
        headers=admin_headers,
        json={
            "name": name,
            "type": type_,
            "webhook_url": f"https://example.test/{name}",
            "secret": "secret",
            "per_minute_limit": 2,
        },
    )
    assert response.status_code == 201
    return response.json()


async def test_admin_channel_authorization_and_push_flow(
    client,
    session_factory,
    fake_redis,
    admin_headers,
    user_headers,
    normal_user,
) -> None:
    ding = await create_channel_via_api(
        client, admin_headers, "ding", ChannelType.DINGTALK_BOT.value
    )
    wecom = await create_channel_via_api(
        client, admin_headers, "wecom", ChannelType.WECOM_BOT.value
    )

    grant = await client.post(
        f"/api/v1/channels/{ding['id']}/permissions/{normal_user.id}",
        headers=admin_headers,
    )
    assert grant.status_code == 200
    grant = await client.post(
        f"/api/v1/channels/{wecom['id']}/permissions/{normal_user.id}",
        headers=admin_headers,
    )
    assert grant.status_code == 200

    key_response = await client.post(
        "/api/v1/push-keys",
        headers=user_headers,
        json={
            "business_name": "ops",
            "per_minute_limit": 2,
            "channel_ids": [ding["id"], wecom["id"]],
            "default_channel_id": ding["id"],
        },
    )
    assert key_response.status_code == 201
    key_payload = key_response.json()
    plaintext_key = key_payload["plaintext_key"]

    get_response = await client.get(
        f"/api/v1/send/{plaintext_key}",
        params={"title": "Ping", "content": "Default only", "type": MessageType.TEXT.value},
    )
    assert get_response.status_code == 200
    assert len(fake_redis.jobs) == 1

    post_response = await client.post(
        "/api/v1/push",
        headers={"Authorization": f"Bearer {plaintext_key}"},
        json={
            "title": "Ping 2",
            "content": "Both channels",
            "type": MessageType.MARKDOWN.value,
            "channel_ids": [ding["id"], wecom["id"]],
        },
    )
    assert post_response.status_code == 200
    assert len(fake_redis.jobs) == 3

    bad_target = await client.post(
        "/api/v1/push",
        headers={"Authorization": f"Bearer {plaintext_key}"},
        json={
            "title": "Bad",
            "content": "Bad",
            "type": MessageType.TEXT.value,
            "channel_ids": ["not-a-channel"],
        },
    )
    assert bad_target.status_code == 400

    async with session_factory() as session:
        messages = list(await session.scalars(select(Message).order_by(Message.created_at.asc())))
        assert len(messages) == 2
        first_deliveries = list(
            await session.scalars(select(Delivery).where(Delivery.message_id == messages[0].id))
        )
        second_deliveries = list(
            await session.scalars(select(Delivery).where(Delivery.message_id == messages[1].id))
        )
        assert len(first_deliveries) == 1
        assert len(second_deliveries) == 2
        assert all(
            delivery.status == DeliveryStatus.QUEUED
            for delivery in first_deliveries + second_deliveries
        )


async def test_push_key_rate_limit_and_disable(
    client,
    session_factory,
    admin_headers,
    user_headers,
    normal_user,
) -> None:
    ding = await create_channel_via_api(
        client, admin_headers, "limit-ding", ChannelType.DINGTALK_BOT.value
    )
    grant = await client.post(
        f"/api/v1/channels/{ding['id']}/permissions/{normal_user.id}",
        headers=admin_headers,
    )
    assert grant.status_code == 200

    key_response = await client.post(
        "/api/v1/push-keys",
        headers=user_headers,
        json={
            "business_name": "limited",
            "per_minute_limit": 1,
            "channel_ids": [ding["id"]],
            "default_channel_id": ding["id"],
        },
    )
    plaintext_key = key_response.json()["plaintext_key"]

    first = await client.post(
        "/api/v1/push",
        headers={"Authorization": f"Bearer {plaintext_key}"},
        json={"title": "Once", "content": "One", "type": MessageType.TEXT.value},
    )
    second = await client.post(
        "/api/v1/push",
        headers={"Authorization": f"Bearer {plaintext_key}"},
        json={"title": "Twice", "content": "Two", "type": MessageType.TEXT.value},
    )
    assert first.status_code == 200
    assert second.status_code == 429

    key_id = key_response.json()["id"]
    disabled = await client.patch(
        f"/api/v1/push-keys/{key_id}",
        headers=user_headers,
        json={"is_active": False},
    )
    assert disabled.status_code == 200

    disabled_push = await client.post(
        "/api/v1/push",
        headers={"Authorization": f"Bearer {plaintext_key}"},
        json={"title": "Blocked", "content": "Nope", "type": MessageType.TEXT.value},
    )
    assert disabled_push.status_code == 403
