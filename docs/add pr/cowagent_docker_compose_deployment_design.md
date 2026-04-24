# Docker Compose 一键部署设计文档

## 1. 目标

本文档定义本项目开发、测试、预发、生产环境的 Docker 化部署策略，确保：

- 支持 Docker 一键部署
- 开发、测试、生产依赖一致
- 数据库与核心中间件类型一致
- 环境差异仅体现在配置、资源、密钥与副本数
- 为后续扩展到 Kubernetes 保留路径

---

## 2. 部署原则

## 2.1 环境一致性硬约束

开发、测试、生产必须使用同类型依赖：

- PostgreSQL
- Redis
- Qdrant
- MinIO

不允许：

- 开发用 SQLite 替代 PostgreSQL
- 测试跳过 Redis
- 测试使用本地文件替代 MinIO
- 测试跳过 Qdrant

## 2.2 镜像一致性

同一版本的 app / worker 镜像应在开发、测试、生产保持一致。

## 2.3 编排一致性

建议统一使用 compose base + env overlay 的方式。

---

## 3. 服务清单

## 3.1 平台部署版

- platform-app
- platform-worker
- platform-web
- postgres
- redis
- qdrant
- minio

## 3.2 外层增强版

- platform-app
- platform-worker
- platform-web
- postgres
- redis
- qdrant
- minio
- nginx
- migrate
- init-buckets
- init-collections

---

## 4. 容器职责

## 4.1 app

职责：

- API
- Gateway
- Control Plane
- Channel ingress
- Runtime orchestration
- 实时请求处理

## 4.2 worker

职责：

- async job
- usage aggregation
- 文档处理
- embedding pipeline
- 重工具执行
- 报表异步任务

## 4.3 postgres

职责：

- 主业务数据库
- usage 聚合表
- pricing catalog
- audit 索引

## 4.4 redis

职责：

- session 热状态
- cache
- rate limit
- quota counter
- Redis Streams

## 4.5 qdrant

职责：

- knowledge vector
- memory vector

## 4.6 minio

职责：

- 上传文件
- artifact
- 导出文件
- 分析结果

## 4.7 nginx（可选）

职责：

- 统一入口
- TLS 终止
- 反向代理
- 静态资源

---

## 5. 目录组织建议

```text
docker/
  compose.base.yml
  compose.platform.yml
  compose.test.yml
  compose.prod.yml
  init/
    minio/
    qdrant/
    postgres/
```

---

## 6. 推荐网络与卷设计

## 6.1 网络

统一一个内部网络：

- `ai_platform_net`

## 6.2 卷

### PostgreSQL
- `pg_data`

### Redis
- `redis_data`

### Qdrant
- `qdrant_data`

### MinIO
- `minio_data`

### App 临时目录
- `app_tmp`

### Worker 临时目录
- `worker_tmp`

---

## 7. 示例 compose.base.yml

```yaml
version: "3.9"

services:
  app:
    image: your-org/ai-platform-app:${APP_TAG}
    env_file:
      - ./env/${ENV}.env
    depends_on:
      - postgres
      - redis
      - qdrant
      - minio
    networks:
      - ai_platform_net
    restart: unless-stopped

  worker:
    image: your-org/ai-platform-worker:${APP_TAG}
    env_file:
      - ./env/${ENV}.env
    depends_on:
      - postgres
      - redis
      - qdrant
      - minio
    networks:
      - ai_platform_net
    restart: unless-stopped

  postgres:
    image: postgres:16
    environment:
      POSTGRES_DB: ai_platform
      POSTGRES_USER: ai_platform
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - pg_data:/var/lib/postgresql/data
    networks:
      - ai_platform_net
    restart: unless-stopped

  redis:
    image: redis:7
    command: ["redis-server", "--appendonly", "yes"]
    volumes:
      - redis_data:/data
    networks:
      - ai_platform_net
    restart: unless-stopped

  qdrant:
    image: qdrant/qdrant:latest
    volumes:
      - qdrant_data:/qdrant/storage
    networks:
      - ai_platform_net
    restart: unless-stopped

  minio:
    image: minio/minio:latest
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: ${MINIO_ROOT_USER}
      MINIO_ROOT_PASSWORD: ${MINIO_ROOT_PASSWORD}
    volumes:
      - minio_data:/data
    networks:
      - ai_platform_net
    restart: unless-stopped

volumes:
  pg_data:
  redis_data:
  qdrant_data:
  minio_data:

networks:
  ai_platform_net:
```

---

## 8. compose.platform.yml 基础应用栈

基础应用栈包含：

- platform-app
- platform-worker
- platform-web
- 全依赖环境变量
- 容器启动前依赖等待
- PostgreSQL schema 幂等迁移

---

## 9. compose.test.yml 已落地约束

测试环境要求：

- 不改变依赖类型
- 使用独立 env
- 自动 migration
- 容器启动前等待 PostgreSQL / Redis / Qdrant / MinIO 全部可用
- `/ready` 纳入四类依赖状态
- 可执行集成测试
- compose 契约测试校验测试环境和生产环境服务集合一致

---

## 10. compose.prod.yml 已落地约束

生产环境要求：

- 使用与测试环境相同的 PostgreSQL / Redis / Qdrant / MinIO 栈
- `restart: unless-stopped`
- 生产密钥通过环境注入
- 默认弱密码直接启动失败
- 生产依赖指向 localhost 直接启动失败
- 持久化卷独立管理
- nginx / TLS / 日志采集可在外层继续接入

---

## 11. 环境变量规范

建议统一前缀：

### 应用
- APP_ENV
- APP_LOG_LEVEL

### PostgreSQL
- POSTGRES_HOST
- POSTGRES_PORT
- POSTGRES_DB
- POSTGRES_USER
- POSTGRES_PASSWORD

### Redis
- REDIS_HOST
- REDIS_PORT
- REDIS_PASSWORD

### Qdrant
- QDRANT_URL

### MinIO
- MINIO_ENDPOINT
- MINIO_ACCESS_KEY
- MINIO_SECRET_KEY
- MINIO_BUCKET_UPLOADS
- MINIO_BUCKET_ARTIFACTS

### Runtime
- DEFAULT_MODEL_PROVIDER
- DEFAULT_WORKSPACE_ROOT

---

## 12. Migration 与初始化

## 12.1 migrate 容器

建议单独提供一个 migration job：

- 等待 postgres 就绪
- 执行 schema migration
- 失败时阻断 app/worker 启动

## 12.2 init-buckets

初始化：

- uploads
- artifacts
- exports
- archives

## 12.3 init-collections

初始化 Qdrant collection 策略或校验脚本。

---

## 13. 健康检查

## 13.1 app

- `/health/live`
- `/health/ready`

## 13.2 worker

- worker 心跳或 `/health`

## 13.3 postgres

- `pg_isready`

## 13.4 redis

- `redis-cli ping`

## 13.5 qdrant

- HTTP health endpoint

## 13.6 minio

- MinIO health endpoint

---

## 14. CI/CD 建议

### CI
- build app image
- build worker image
- run unit tests
- run contract tests
- run compose-based integration tests
- validate migration

### CD
- push image
- run migration job
- deploy app/worker
- smoke test
- rollback on failure

---

## 15. 本地开发启动命令建议

```bash
docker compose -f docker/compose.base.yml -f docker/compose.platform.yml up -d --build
```

## 测试环境

```bash
docker compose -p cowagent-test \
  -f docker/compose.base.yml \
  -f docker/compose.platform.yml \
  -f docker/compose.test.yml \
  up -d --build
```

## 生产环境

```bash
PLATFORM_POSTGRES_PASSWORD='change-to-strong-db-secret' \
PLATFORM_MINIO_ROOT_USER='change-to-prod-access' \
PLATFORM_MINIO_ROOT_PASSWORD='change-to-strong-minio-secret' \
docker compose -p cowagent-prod \
  -f docker/compose.base.yml \
  -f docker/compose.platform.yml \
  -f docker/compose.prod.yml \
  up -d --build
```

---

## 16. 环境一致性红线

1. 禁止开发环境用 SQLite 替代 PostgreSQL
2. 禁止测试环境绕过 Redis
3. 禁止测试环境用本地文件替代 MinIO
4. 禁止测试环境不启用 Qdrant
5. 禁止不同环境使用不同 migration 版本
6. 禁止手工改生产 schema
7. 禁止仅在生产启用核心依赖

---

## 17. 未来扩展

如果后续规模增加：

- worker 可横向扩容
- app 可多副本
- Redis Streams 可升级为 RabbitMQ / Kafka
- usage analytics 可增加 ClickHouse
- compose 方案可平滑迁移到 Kubernetes

前提是镜像、依赖与配置模型保持一致。
