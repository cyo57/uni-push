# UniPush

统一消息推送网关。业务侧只对接一个 API，平台负责鉴权、路由、异步分发、失败重试、审计和日志追踪。

## 技术栈

- 后端：FastAPI、SQLAlchemy、Alembic、Redis、Arq
- 前端：React 19、Vite、Tailwind、React Query
- 运行：`uv`、`npm`、`podman compose`
- 数据库：SQLite / MySQL / PostgreSQL

## 本地启动

1. 安装依赖

```bash
uv sync
cd web && npm install
```

2. 启动依赖

```bash
podman compose up -d
```

默认 `podman compose` 编排使用 SQLite。  
如需 PostgreSQL，可启用 `postgres` profile 并改写 `DATABASE_URL`。  
本机直接运行 API / worker 时，也可以把 `.env` 中 `DATABASE_URL` 改成 SQLite / MySQL / PostgreSQL。

3. 执行迁移并初始化管理员

```bash
uv run alembic upgrade head
uv run seed-admin
```

4. 启动后端、worker 和前端

```bash
uv run unipush-api
uv run arq app.workers.arq.WorkerSettings
cd web && npm run dev
```

默认控制台地址：`http://localhost:5173`

## Podman Compose 一键运行

```bash
cp .env.example .env
podman compose up --build -d
```

默认访问地址：`http://localhost:8000`

修改指定用户密码：

```bash
uv run reset-password --username admin --password new-password-123
```

## 核心能力

- 管理员与普通用户双角色控制台
- 渠道管理、用户直授权、用户组授权、Push Key 管理
- 当前已支持渠道：企业微信机器人、钉钉机器人
- 当前已支持扩展渠道：飞书机器人、自定义 Webhook
- `POST /api/v1/push` Bearer Push Key 鉴权，支持 `Idempotency-Key` 幂等键与可选 `channel_ids[]` 定向发送
- Redis 异步分发、指数退避重试、死信治理、卡住投递自动修复、Key/Channel 双层限流
- 渠道密钥加密存储，消息日志仅保留脱敏后的请求与响应摘要
- 消息支持筛选、导出、整条重放、失败/死信投递重试
- 审计日志覆盖登录、用户、用户组、渠道、授权、Push Key、消息重放与人工重试
- 控制台支持个人设置与密码修改
- 提供 `/livez`、`/readyz`、`/metrics`，并包含 worker 心跳与积压/死信指标

## 测试

后端：

```bash
uv run pytest app/tests -q
```

前端：

```bash
cd web && npm run lint && npm run build
```

当前仓库尚未接入独立的前端自动化测试脚本。

## 文档

- API 摘要：`docs/api.md`
- 部署说明：`docs/deployment.md`
- 运维与排障：`docs/operations.md`
