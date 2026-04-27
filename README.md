# UniPush

统一消息推送网关。业务侧只对接一个 API，平台负责鉴权、路由、异步分发、失败重试和日志追踪。

## 技术栈

- 后端：FastAPI、SQLAlchemy、Alembic、Redis、Arq
- 前端：React 19、Vite、Tailwind、React Query
- 运行：`uv`、`npm`、`podman compose`

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

修改指定用户密码：

```bash
uv run reset-password --username admin --password new-password-123
```

## 核心能力

- 管理员与普通用户双角色控制台
- 渠道管理、授权管理、Push Key 管理
- `GET /api/v1/send/{push_key}` 默认渠道发送
- `POST /api/v1/push` 可选 `channel_ids[]` 定向发送
- Redis 异步分发、指数退避重试、Key/Channel 双层限流
- 消息日志详情包含原始请求体和第三方原始响应体

## 测试

后端：

```bash
uv run pytest app/tests -q
```

前端：

```bash
cd web && npm run lint && npm run test && npm run build
```
