from sqlalchemy import select

from app.core.enums import ChannelType, DeliveryStatus, MessageSource, MessageStatus, MessageType
from app.models.audit import AuditLog
from app.models.message import Delivery, Message
from app.models.push_key import PushKey, PushKeyChannel


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


async def authorize_channels_for_user_via_group(
    client,
    admin_headers,
    user_id: str,
    group_name: str,
    channel_ids: list[str],
) -> str:
    group_response = await client.post(
        "/api/v1/groups",
        headers=admin_headers,
        json={"name": group_name, "description": group_name},
    )
    assert group_response.status_code == 201
    group_id = group_response.json()["id"]

    for channel_id in channel_ids:
        grant_channel = await client.post(
            f"/api/v1/groups/{group_id}/channels/{channel_id}",
            headers=admin_headers,
        )
        assert grant_channel.status_code == 200

    grant_member = await client.post(
        f"/api/v1/groups/{group_id}/members/{user_id}",
        headers=admin_headers,
    )
    assert grant_member.status_code == 200
    return group_id


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

    await authorize_channels_for_user_via_group(
        client,
        admin_headers,
        normal_user.id,
        "auth-flow-group",
        [ding["id"], wecom["id"]],
    )

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

    post_response = await client.post(
        "/api/v1/push",
        headers={"Authorization": f"Bearer {plaintext_key}"},
        json={
            "title": "Ping",
            "content": "Both channels",
            "type": MessageType.MARKDOWN.value,
            "channel_ids": [ding["id"], wecom["id"]],
        },
    )
    assert post_response.status_code == 200
    assert len(fake_redis.jobs) == 2

    removed_get = await client.get(
        f"/api/v1/send/{plaintext_key}",
        params={"title": "Ping", "content": "Removed", "type": MessageType.TEXT.value},
    )
    assert removed_get.status_code == 404

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
        assert len(messages) == 1
        deliveries = list(
            await session.scalars(select(Delivery).where(Delivery.message_id == messages[0].id))
        )
        assert len(deliveries) == 2
        assert all(delivery.status == DeliveryStatus.QUEUED for delivery in deliveries)


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
    await authorize_channels_for_user_via_group(
        client,
        admin_headers,
        normal_user.id,
        "limit-group",
        [ding["id"]],
    )

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


async def test_post_push_rejects_oversized_content(
    client,
    fake_redis,
    admin_headers,
    user_headers,
    normal_user,
) -> None:
    ding = await create_channel_via_api(
        client, admin_headers, "oversize-ding", ChannelType.DINGTALK_BOT.value
    )
    await authorize_channels_for_user_via_group(
        client,
        admin_headers,
        normal_user.id,
        "oversize-group",
        [ding["id"]],
    )

    key_response = await client.post(
        "/api/v1/push-keys",
        headers=user_headers,
        json={
            "business_name": "oversize",
            "per_minute_limit": 5,
            "channel_ids": [ding["id"]],
            "default_channel_id": ding["id"],
        },
    )
    assert key_response.status_code == 201
    plaintext_key = key_response.json()["plaintext_key"]

    response = await client.post(
        "/api/v1/push",
        headers={"Authorization": f"Bearer {plaintext_key}"},
        json={
            "title": "Too large",
            "content": "a" * (10 * 1024 + 1),
            "type": MessageType.TEXT.value,
        },
    )

    assert response.status_code == 413
    assert response.json()["detail"] == "Content is too large"
    assert fake_redis.jobs == []


async def test_dashboard_stats_counts_authorized_channels_for_normal_user(
    client,
    admin_headers,
    user_headers,
    normal_user,
) -> None:
    ding = await create_channel_via_api(
        client, admin_headers, "stats-ding", ChannelType.DINGTALK_BOT.value
    )
    wecom = await create_channel_via_api(
        client, admin_headers, "stats-wecom", ChannelType.WECOM_BOT.value
    )
    hidden = await create_channel_via_api(
        client, admin_headers, "stats-hidden", ChannelType.DINGTALK_BOT.value
    )

    await authorize_channels_for_user_via_group(
        client,
        admin_headers,
        normal_user.id,
        "stats-group",
        [ding["id"], wecom["id"]],
    )

    user_stats = await client.get("/api/v1/dashboard/stats", headers=user_headers)
    admin_stats = await client.get("/api/v1/dashboard/stats", headers=admin_headers)

    assert user_stats.status_code == 200
    assert user_stats.json()["total_channels"] == 2
    assert admin_stats.status_code == 200
    assert admin_stats.json()["total_channels"] == 3
    assert hidden["id"] not in {ding["id"], wecom["id"]}


async def test_update_current_user_profile_and_password(client, user_headers) -> None:
    update_profile = await client.patch(
        "/api/v1/auth/me",
        headers=user_headers,
        json={"display_name": "Updated User"},
    )
    assert update_profile.status_code == 200
    assert update_profile.json()["user"]["display_name"] == "Updated User"
    assert update_profile.json()["access_token"] is None

    change_password = await client.patch(
        "/api/v1/auth/me",
        headers=user_headers,
        json={"current_password": "user-pass", "new_password": "user-pass-2"},
    )
    assert change_password.status_code == 200
    rotated_token = change_password.json()["access_token"]
    assert isinstance(rotated_token, str)

    refresh = await client.post(
        "/api/v1/auth/refresh",
        headers={"Authorization": f"Bearer {rotated_token}"},
    )
    assert refresh.status_code == 200

    login_old = await client.post(
        "/api/v1/auth/login",
        json={"username": "user", "password": "user-pass"},
    )
    login_new = await client.post(
        "/api/v1/auth/login",
        json={"username": "user", "password": "user-pass-2"},
    )
    assert login_old.status_code == 401
    assert login_new.status_code == 200


async def test_login_rate_limit(client, session_factory, fake_redis) -> None:
    for _ in range(10):
        response = await client.post(
            "/api/v1/auth/login",
            json={"username": "missing", "password": "bad-password"},
        )
        assert response.status_code == 401

    limited = await client.post(
        "/api/v1/auth/login",
        json={"username": "missing", "password": "bad-password"},
    )
    assert limited.status_code == 429


async def test_message_filters_export_replay_and_retry(
    client,
    session_factory,
    fake_redis,
    admin_headers,
    user_headers,
    normal_user,
) -> None:
    channel = await create_channel_via_api(
        client, admin_headers, "message-ops", ChannelType.GENERIC_WEBHOOK.value
    )
    await authorize_channels_for_user_via_group(
        client,
        admin_headers,
        normal_user.id,
        "message-filter-group",
        [channel["id"]],
    )

    key_response = await client.post(
        "/api/v1/push-keys",
        headers=user_headers,
        json={
            "business_name": "ops-search",
            "per_minute_limit": 10,
            "channel_ids": [channel["id"]],
            "default_channel_id": channel["id"],
        },
    )
    assert key_response.status_code == 201
    plaintext_key = key_response.json()["plaintext_key"]

    first_push = await client.post(
        "/api/v1/push",
        headers={"Authorization": f"Bearer {plaintext_key}"},
        json={"title": "Deploy failed", "content": "alpha", "type": MessageType.TEXT.value},
    )
    second_push = await client.post(
        "/api/v1/push",
        headers={"Authorization": f"Bearer {plaintext_key}"},
        json={"title": "Cache warm", "content": "beta", "type": MessageType.TEXT.value},
    )
    assert first_push.status_code == 200
    assert second_push.status_code == 200

    filtered = await client.get(
        "/api/v1/messages",
        headers=user_headers,
        params={"q": "Deploy", "status": MessageStatus.QUEUED.value},
    )
    assert filtered.status_code == 200
    assert filtered.json()["total"] == 1
    assert filtered.json()["items"][0]["user_display_name"] == normal_user.display_name
    assert filtered.json()["items"][0]["channel_names"] == [channel["name"]]

    exported = await client.get(
        "/api/v1/messages/export",
        headers=user_headers,
        params={"q": "Deploy"},
    )
    assert exported.status_code == 200
    assert "Deploy failed" in exported.text

    login_view = await client.get("/api/v1/channels", headers=admin_headers)
    assert login_view.status_code == 200
    assert login_view.json()["items"][0]["secret"] is None
    assert login_view.json()["items"][0]["has_secret"] is True

    replayed = await client.post(
        f"/api/v1/messages/{first_push.json()['data']['message_id']}/replay",
        headers=user_headers,
    )
    assert replayed.status_code == 200
    assert replayed.json()["message_id"].startswith("msg_")

    async with session_factory() as session:
        message = await session.scalar(
            select(Message).where(Message.id == first_push.json()["data"]["message_id"])
        )
        assert message is not None
        delivery = await session.scalar(select(Delivery).where(Delivery.message_id == message.id))
        assert delivery is not None
        delivery.status = DeliveryStatus.FAILED
        delivery.final_error = "manual failure"
        message.status = MessageStatus.FAILED
        await session.commit()
        delivery_id = delivery.id

    retried = await client.post(
        f"/api/v1/messages/{first_push.json()['data']['message_id']}/deliveries/{delivery_id}/retry",
        headers=user_headers,
    )
    assert retried.status_code == 204
    assert any(job["args"][0] == delivery_id for job in fake_redis.jobs)


async def test_group_permissions_enable_channel_access_and_audit_logs(
    client,
    session_factory,
    admin_headers,
    user_headers,
    normal_user,
) -> None:
    channel = await create_channel_via_api(
        client,
        admin_headers,
        "group-channel",
        ChannelType.GENERIC_WEBHOOK.value,
    )

    group_response = await client.post(
        "/api/v1/groups",
        headers=admin_headers,
        json={"name": "ops-group", "description": "ops"},
    )
    assert group_response.status_code == 201
    group_id = group_response.json()["id"]

    grant_channel = await client.post(
        f"/api/v1/groups/{group_id}/channels/{channel['id']}",
        headers=admin_headers,
    )
    assert grant_channel.status_code == 200

    grant_member = await client.post(
        f"/api/v1/groups/{group_id}/members/{normal_user.id}",
        headers=admin_headers,
    )
    assert grant_member.status_code == 200

    visible_channels = await client.get("/api/v1/channels", headers=user_headers)
    assert visible_channels.status_code == 200
    assert visible_channels.json()["total"] == 1
    assert visible_channels.json()["items"][0]["authorized_group_ids"] == [group_id]

    key_response = await client.post(
        "/api/v1/push-keys",
        headers=user_headers,
        json={
            "business_name": "group-bound",
            "per_minute_limit": 5,
            "channel_ids": [channel["id"]],
            "default_channel_id": channel["id"],
        },
    )
    assert key_response.status_code == 201

    audit_response = await client.get(
        "/api/v1/audit-logs",
        headers=admin_headers,
        params={"target_type": "group"},
    )
    assert audit_response.status_code == 200
    actions = {item["action"] for item in audit_response.json()["items"]}
    assert {"group.create", "group.channel.grant", "group.member.grant"}.issubset(actions)

    delete_group = await client.delete(f"/api/v1/groups/{group_id}", headers=admin_headers)
    assert delete_group.status_code == 204

    async with session_factory() as session:
        group_audits = list(
            await session.scalars(select(AuditLog).where(AuditLog.target_type == "group"))
        )
        assert len(group_audits) >= 4


async def test_user_group_assignment_filters_and_push_key_delete(
    client,
    fake_redis,
    admin_headers,
    user_headers,
    normal_user,
) -> None:
    group_response = await client.post(
        "/api/v1/groups",
        headers=admin_headers,
        json={"name": "filter-group", "description": "filters"},
    )
    assert group_response.status_code == 201
    group_id = group_response.json()["id"]

    created_user = await client.post(
        "/api/v1/users",
        headers=admin_headers,
        json={
          "username": "filter-user",
          "display_name": "Filter User",
          "password": "filter-user-pass",
          "role": "user",
          "group_ids": [group_id],
        },
    )
    assert created_user.status_code == 201
    assert created_user.json()["group_ids"] == [group_id]

    filtered_users = await client.get(
        "/api/v1/users",
        headers=admin_headers,
        params={"group_ids": group_id, "statuses": "active"},
    )
    assert filtered_users.status_code == 200
    assert filtered_users.json()["total"] >= 1

    updated_user = await client.patch(
        f"/api/v1/users/{normal_user.id}",
        headers=admin_headers,
        json={"group_ids": [group_id]},
    )
    assert updated_user.status_code == 200
    assert updated_user.json()["group_ids"] == [group_id]

    filtered_groups = await client.get(
        "/api/v1/groups",
        headers=admin_headers,
        params={"member_user_ids": normal_user.id},
    )
    assert filtered_groups.status_code == 200
    assert any(item["id"] == group_id for item in filtered_groups.json()["items"])

    channel = await create_channel_via_api(
        client, admin_headers, "delete-key-channel", ChannelType.GENERIC_WEBHOOK.value
    )
    grant_channel = await client.post(
        f"/api/v1/groups/{group_id}/channels/{channel['id']}",
        headers=admin_headers,
    )
    assert grant_channel.status_code == 200

    key_response = await client.post(
        "/api/v1/push-keys",
        headers=user_headers,
        json={
            "business_name": "delete-key",
            "per_minute_limit": 5,
            "channel_ids": [channel["id"]],
            "default_channel_id": channel["id"],
        },
    )
    assert key_response.status_code == 201

    push_response = await client.post(
        "/api/v1/push",
        headers={"Authorization": f"Bearer {key_response.json()['plaintext_key']}"},
        json={"title": "cleanup", "content": "cleanup", "type": MessageType.TEXT.value},
    )
    assert push_response.status_code == 200
    assert len(fake_redis.jobs) >= 1

    deleted = await client.delete(
        f"/api/v1/push-keys/{key_response.json()['id']}",
        headers=user_headers,
    )
    assert deleted.status_code == 200
    assert deleted.json()["id"] == key_response.json()["id"]


async def test_push_idempotency_key_deduplicates_requests(
    client,
    session_factory,
    fake_redis,
    admin_headers,
    user_headers,
    normal_user,
) -> None:
    channel = await create_channel_via_api(
        client,
        admin_headers,
        "idem-channel",
        ChannelType.WECOM_BOT.value,
    )
    await authorize_channels_for_user_via_group(
        client,
        admin_headers,
        normal_user.id,
        "idem-group",
        [channel["id"]],
    )

    key_response = await client.post(
        "/api/v1/push-keys",
        headers=user_headers,
        json={
            "business_name": "idem",
            "per_minute_limit": 1,
            "channel_ids": [channel["id"]],
            "default_channel_id": channel["id"],
        },
    )
    assert key_response.status_code == 201
    plaintext_key = key_response.json()["plaintext_key"]

    first = await client.post(
        "/api/v1/push",
        headers={
            "Authorization": f"Bearer {plaintext_key}",
            "Idempotency-Key": "idem-1",
        },
        json={"title": "Same", "content": "body", "type": MessageType.TEXT.value},
    )
    second = await client.post(
        "/api/v1/push",
        headers={
            "Authorization": f"Bearer {plaintext_key}",
            "Idempotency-Key": "idem-1",
        },
        json={"title": "Same", "content": "body", "type": MessageType.TEXT.value},
    )
    conflict = await client.post(
        "/api/v1/push",
        headers={
            "Authorization": f"Bearer {plaintext_key}",
            "Idempotency-Key": "idem-1",
        },
        json={"title": "Same", "content": "changed", "type": MessageType.TEXT.value},
    )

    assert first.status_code == 200
    assert first.json()["data"]["deduplicated"] is False
    assert second.status_code == 200
    assert second.json()["data"]["deduplicated"] is True
    assert second.json()["data"]["message_id"] == first.json()["data"]["message_id"]
    assert conflict.status_code == 409
    assert len(fake_redis.jobs) == 1

    async with session_factory() as session:
        messages = list(await session.scalars(select(Message)))
        assert len(messages) == 1


async def test_dashboard_detail_endpoints(
    client,
    session_factory,
    admin_headers,
    admin_user,
) -> None:
    from app.core.security import hash_password
    from app.models.channel import Channel
    from app.models.user import User

    async with session_factory() as session:
        seeded_user = User(
            username="dash-owner",
            display_name="Dash Owner",
            password_hash=hash_password("dash-pass"),
            role=admin_user.role,
            is_active=True,
        )
        seeded_channel = Channel(
            name="dash-channel",
            type=ChannelType.FEISHU_BOT,
            webhook_url="https://example.test/feishu",
            is_enabled=True,
            per_minute_limit=10,
        )
        session.add_all([seeded_user, seeded_channel])
        await session.flush()
        push_key = PushKey(
            user_id=seeded_user.id,
            business_name="dash-key",
            key_hash="dash-hash",
            key_hint="dash...",
            is_active=True,
            per_minute_limit=10,
            default_channel_id=seeded_channel.id,
        )
        session.add(push_key)
        await session.flush()
        session.add(PushKeyChannel(push_key_id=push_key.id, channel_id=seeded_channel.id))
        message = Message(
            id="msg_dashboard_seed",
            user_id=seeded_user.id,
            push_key_id=push_key.id,
            source=MessageSource.POST,
            title="dashboard",
            content="seed",
            message_type=MessageType.TEXT,
            requested_channel_ids=[seeded_channel.id],
            request_payload={},
            status=MessageStatus.FAILED,
        )
        session.add(message)
        session.add(
            Delivery(
                id="delivery_dashboard_seed",
                message_id=message.id,
                channel_id=seeded_channel.id,
                status=DeliveryStatus.FAILED,
                adapter_payload={},
                attempt_logs=[],
                final_error="seed error",
            )
        )
        await session.commit()

    hot_keys = await client.get("/api/v1/dashboard/hot-keys", headers=admin_headers)
    error_reasons = await client.get("/api/v1/dashboard/error-reasons", headers=admin_headers)
    channel_perf = await client.get("/api/v1/dashboard/channel-performance", headers=admin_headers)
    channel_usage = await client.get("/api/v1/dashboard/channels", headers=admin_headers)

    assert hot_keys.status_code == 200
    assert hot_keys.json()[0]["business_name"] == "dash-key"
    assert error_reasons.status_code == 200
    assert error_reasons.json()[0]["reason"] == "seed error"
    assert channel_perf.status_code == 200
    assert channel_perf.json()[0]["channel_name"] == "dash-channel"
    assert channel_usage.status_code == 200
    assert channel_usage.json()[0]["name"] == "dash-channel"
