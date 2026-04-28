# UniPush 部署说明

## 依赖

- Podman / Docker
- Podman Compose / Docker Compose

## 环境变量

参考根目录 `.env.example`：

- `DATABASE_URL`
- `REDIS_URL`
- `JWT_SECRET`
- `DATA_ENCRYPTION_KEY`
- `JWT_EXPIRE_MINUTES`
- `LOG_RETENTION_DAYS`
- `LOGIN_RATE_LIMIT_PER_MINUTE`
- `SENSITIVE_LOG_MAX_BYTES`
- `DELIVERY_STALE_AFTER_SECONDS`
- `WORKER_HEARTBEAT_TTL_SECONDS`
- `CORS_ORIGINS`
- `BOOTSTRAP_ADMIN_USERNAME`
- `BOOTSTRAP_ADMIN_PASSWORD`
- `BOOTSTRAP_ADMIN_DISPLAY_NAME`

### 数据库选择

- SQLite：`sqlite+aiosqlite:///./unipush.db`
- MySQL：`mysql+asyncmy://unipush:unipush@localhost:3306/unipush`
- PostgreSQL：`postgresql+asyncpg://unipush:unipush@localhost:5432/unipush`

建议：

- SQLite：开发、单机、轻量环境
- PostgreSQL：默认推荐生产库
- MySQL：兼容接入场景

## 启动

```bash
cp .env.example .env
podman compose up --build -d
```

服务说明：

- `api`：FastAPI + 已构建前端静态资源
- `worker`：ARQ 投递与日志清理
- `postgres`：可选 profile 数据库
- `redis`：限流与任务队列

默认 `podman compose up -d` 使用 SQLite 持久卷。  
如需 PostgreSQL，可额外启用：

```bash
podman compose --profile postgres up -d
```

默认访问：

```bash
http://localhost:8000
```

健康检查：

```bash
curl http://localhost:8000/livez
curl http://localhost:8000/readyz
curl http://localhost:8000/metrics
```

## 生产建议

- 使用反向代理统一暴露前端和 `/api`
- 将 `JWT_SECRET` 替换为强随机值
- 将 `DATA_ENCRYPTION_KEY` 设置为独立强随机值
- 为 API 与 worker 分别配置进程守护
