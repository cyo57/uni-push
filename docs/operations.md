# UniPush 运维与排障

## 健康检查

- `GET /healthz`
- `GET /livez`
- `GET /readyz`
- `GET /metrics`

`/readyz` 除数据库和 Redis 以外，还会检查 worker 心跳是否存在。

## 常见操作

### 初始化管理员

```bash
uv run seed-admin
```

### 重置密码

```bash
uv run reset-password --username admin --password new-password-123
```

### 执行迁移

```bash
uv run alembic upgrade head
```

## 常见问题

### API 可以登录，但消息未投递

优先检查：

1. Redis 是否可用
2. worker 是否已启动
3. `/readyz` 是否提示 `worker heartbeat missing`
4. 对应通道是否启用
5. Push Key 是否停用
6. 消息详情里的第三方响应体、重试时间和最终错误信息

### 消息一直停留在 sending / retrying

优先检查：

1. `/metrics` 中 `unipush_deliveries_inflight`
2. worker 是否持续运行
3. `DELIVERY_STALE_AFTER_SECONDS` 是否过长
4. 等待 worker 的卡住投递修复定时任务自动回补

系统会把长时间卡住的 `queued / retrying / sending` 投递重新排队。

### 死信数量持续增长

优先检查：

1. `/metrics` 中 `unipush_deliveries_dead_letter_total`
2. 目标 webhook 是否长期返回 4xx
3. 渠道 Secret、签名、机器人权限是否变更
4. 是否需要人工执行失败/死信投递重试

### 通道测试失败

优先检查：

1. Webhook 地址是否正确
2. Secret 是否正确
3. 第三方机器人是否启用 IP / 签名限制

### 日志被自动清理

消息日志按 `LOG_RETENTION_DAYS` 保留，worker 会定时清理过期数据。

### 审计排查

管理员可通过 `GET /api/v1/audit-logs` 查询：

- 登录成功/失败
- 用户与用户组变更
- 渠道授权与组授权
- Push Key 创建、修改、轮换
- 消息重放与投递重试
