# UniPush API 摘要

## 认证

- `POST /api/v1/auth/login`
- `POST /api/v1/auth/refresh`
- `GET /api/v1/auth/me`
- `PATCH /api/v1/auth/me`

## 通道管理

- `GET /api/v1/channels`
- `POST /api/v1/channels`
- `PATCH /api/v1/channels/{channel_id}`
- `DELETE /api/v1/channels/{channel_id}`
- `POST /api/v1/channels/{channel_id}/test`
- `POST /api/v1/channels/{channel_id}/permissions/{user_id}`
- `DELETE /api/v1/channels/{channel_id}/permissions/{user_id}`

## 用户组与组权限

- `GET /api/v1/groups`
- `POST /api/v1/groups`
- `PATCH /api/v1/groups/{group_id}`
- `DELETE /api/v1/groups/{group_id}`
- `POST /api/v1/groups/{group_id}/members/{user_id}`
- `DELETE /api/v1/groups/{group_id}/members/{user_id}`
- `POST /api/v1/groups/{group_id}/channels/{channel_id}`
- `DELETE /api/v1/groups/{group_id}/channels/{channel_id}`

当前支持通道：

- `wecom_bot`
- `dingtalk_bot`
- `feishu_bot`
- `generic_webhook`

## Push Key

- `GET /api/v1/push-keys`
- `POST /api/v1/push-keys`
- `PATCH /api/v1/push-keys/{push_key_id}`
- `POST /api/v1/push-keys/{push_key_id}/rotate`

## 消息发送

- `POST /api/v1/push`
  - Header: `Authorization: Bearer <push_key>`
  - 可选 Header: `Idempotency-Key: <client-generated-key>`

## 消息记录

- `GET /api/v1/messages`
  - 查询参数：`offset`、`limit`、`q`、`status`
- `GET /api/v1/messages/export`
- `GET /api/v1/messages/{message_id}`
- `POST /api/v1/messages/{message_id}/replay`
- `POST /api/v1/messages/{message_id}/deliveries/{delivery_id}/retry`

## Dashboard

- `GET /api/v1/dashboard/summary`
- `GET /api/v1/dashboard/stats`
- `GET /api/v1/dashboard/requests`
- `GET /api/v1/dashboard/channels`
- `GET /api/v1/dashboard/error-reasons`
- `GET /api/v1/dashboard/hot-keys`
- `GET /api/v1/dashboard/channel-performance`

## 审计日志

- `GET /api/v1/audit-logs`
  - 查询参数：`offset`、`limit`、`action`、`target_type`、`actor_user_id`
