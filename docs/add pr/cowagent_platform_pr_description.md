# CowAgent AI 中台化改造 PR 说明

## 1. 建议 PR 标题

`feat: 将 CowAgent 渐进式改造为支持多租户、多 Agent、隔离记忆与异步 Worker 的 AI 中台`

---

## 2. 背景

当前 CowAgent 更适合“单实例、单全局配置、单工作区”的通用 Agent 引擎形态。  
本次改造的目标不是重写 CowAgent，而是在尽量保持上游兼容的前提下，把它逐步演进为：

- 支持多租户
- 支持显性多 Agent
- 支持独立会话 / 记忆 / 梦境 / 知识空间
- 支持渠道绑定
- 支持 usage / cost / quota
- 支持独立 worker 和异步任务
- 支持 Docker 一键部署
- 支持后续持续吸收上游更新

本 PR 采用的是“平台层新增 + 内核兼容桥接”的渐进式路线，而不是一次性重构内核。

---

## 3. 改造范围总览

本次改造新增平台层目录 `cow_platform/`，并在少量上游关键文件上做兼容 patch，使项目同时支持：

- legacy 模式：
  继续使用现有 `app.py`、根 `config.json`、单工作区运行
- platform 模式：
  使用显式 `tenant_id / agent_id / binding_id / session_id` 驱动运行时

主要新增能力包括：

1. 平台领域模型与 API 骨架
2. 单租户显性多 Agent
3. 多租户与渠道绑定
4. usage / cost / quota
5. 独立 worker 与异步任务
6. 审计日志、doctor、自检文档、patch register、升级 SOP

---

## 4. 分阶段交付结果

## Phase 0：平台骨架与测试基线

已完成：

- 新增 `cow_platform/` 目录骨架
- 新增 `RuntimeContext`、`AgentDefinition`、`SessionState`、`PolicySnapshot`
- 新增平台 API：
  - `/health`
  - `/ready`
- 新增 Docker 基础依赖编排：
  - PostgreSQL
  - Redis
  - Qdrant
  - MinIO
- 新增 PostgreSQL 幂等 schema 初始化入口：
  - `python -m cow_platform.db.migrate`
- 建立 `unit / integration / e2e` 三层测试基线

目的：

- 不先改旧业务主链路
- 先把平台化改造的安全底座搭起来

## Phase 1：单租户显性多 Agent

已完成：

- 新增 Agent 资源与 PostgreSQL 仓储
- 支持通过平台 API 创建 / 查询 / 更新 Agent
- 新增 `CowAgentRuntimeAdapter`
- 支持按 `agent_id` 切换：
  - workspace
  - prompt
  - model
  - session store
  - memory / knowledge / dreams
- `channel/web` 支持显式选择 Agent
- ConversationStore 已迁移到 PostgreSQL，并按 `tenant_id + agent_id + session_id` 隔离
- 长期记忆索引已从本地 SQLite 文件迁移到 PostgreSQL，并按 workspace namespace 隔离

效果：

- 单租户下多个 Agent 可以并行存在
- 不同 Agent 的会话、记忆索引、知识、梦境文件互不串扰

## Phase 2：多租户与渠道绑定

已完成：

- 新增 `Tenant` 与 `ChannelBinding`
- 平台 API 支持 tenant / binding CRUD
- Web 渠道支持：
  - `agent_id` 直连
  - `binding_id -> tenant_id + agent_id` 路由
- 前端 Web 控制台支持：
  - Agent 选择器
  - binding 选择器

效果：

- 多租户资源已成为平台一等资源
- 请求不再只依赖单工作区或单 Agent 假设

## Phase 3：usage / cost / quota

已完成：

- 新增本地 pricing catalog
- 新增 usage ledger
- 新增 tenant / agent 两级日配额
- 平台 API 支持：
  - `/api/platform/pricing`
  - `/api/platform/usage`
  - `/api/platform/costs`
  - `/api/platform/quotas`
- `AgentBridge` 已接入：
  - 请求前 quota 校验
  - 请求后 usage 记录

说明：

- 当前 token 为项目内估算值
- 成本为本地 pricing 计算出的 Direct Cost
- 本期不做商业计费或余额扣费

## Phase 4：独立 worker 与异步任务

已完成：

- 新增 `JobDefinition`
- 新增 PostgreSQL `JobRepository`
- 新增 `JobService`
- 新增独立 worker 入口：
  - `python -m cow_platform.worker.main`
- 新增平台任务 API：
  - `/api/platform/jobs`
- 新增 CLI：
  - `cow platform serve`
  - `cow platform worker`
- 新增 Docker 平台 compose：
  - `platform-app`
  - `platform-worker`
  - `platform-web`
- 新增环境 overlay：
  - `docker/compose.test.yml`
  - `docker/compose.prod.yml`
- `platform-app / platform-worker / platform-web` 统一通过同一组环境变量连接：
  - PostgreSQL：`COW_PLATFORM_DATABASE_URL`
  - Redis：`COW_PLATFORM_REDIS_URL`
  - Qdrant：`COW_PLATFORM_QDRANT_URL`
  - MinIO：`COW_PLATFORM_MINIO_ENDPOINT`
- 容器启动时执行：
  - 全依赖等待与环境校验：`python -m cow_platform.deployment.check --require-all`
  - PostgreSQL schema 幂等迁移：`python -m cow_platform.db.migrate`
- 生产 overlay 会强制：
  - `COW_PLATFORM_ENV=production`
  - `COW_PLATFORM_REQUIRE_DEPENDENCIES=true`
  - `COW_PLATFORM_STRICT_STARTUP=true`
  - 默认弱密码 / localhost 生产依赖直接失败

当前落地的任务类型：

- `usage_report`

效果：

- 平台 app、worker、web 已完成独立部署单元拆分
- 异步任务链路已真实可跑，任务状态和 worker claim 使用 PostgreSQL 行级锁持久化
- 测试环境和生产环境使用同一套基础依赖：PostgreSQL / Redis / Qdrant / MinIO

## Phase 5：稳定性与治理

已完成：

- 新增审计日志：
  - `/api/platform/audit-logs`
- 新增平台 doctor：
  - `/api/platform/doctor`
  - `cow platform doctor`
- `/ready` 已纳入 PostgreSQL / Redis / Qdrant / MinIO 依赖状态
- 新增部署环境校验：
  - `cow_platform/deployment/checks.py`
  - `python -m cow_platform.deployment.check`
- 新增 compose 契约测试，防止测试和生产依赖漂移
- 新增治理文档：
  - `docs/adr/0001-platform-dual-mode-compatibility.md`
  - `docs/patch-register.md`
  - `docs/upstream-upgrade-sop.md`

效果：

- 平台具备基本可追踪性
- 升级和兼容策略从口头约定变成仓库内显式文档

---

## 5. 关键实现点

### 5.1 平台层新增，避免业务散落到上游目录

新增代码主要集中在：

- `cow_platform/domain`
- `cow_platform/repositories`
- `cow_platform/services`
- `cow_platform/api`
- `cow_platform/worker`

这样做的目的，是让平台功能尽量在平台层闭合，上游目录只保留少量兼容 patch。

### 5.2 运行时从“隐式全局”逐步变为“显式作用域”

平台请求会显式携带：

- `tenant_id`
- `agent_id`
- `binding_id`
- `session_id`
- `request_id`

并通过 runtime scope 传递到现有 CowAgent 内核，减少对单全局状态的依赖。

### 5.3 Legacy 与 Platform 双模式并存

当前实现没有移除旧入口，而是形成双模式：

- legacy 用户不受影响
- platform 能力可逐步增强

这是为了降低迁移风险，也便于持续吸收上游更新。

---

## 6. 兼容与升级策略

本 PR 明确采用：

- 平台能力新增到 `cow_platform/`
- 上游关键 patch 点登记到 `docs/patch-register.md`
- 升级流程固化到 `docs/upstream-upgrade-sop.md`

当前已登记的重要 patch 触点包括：

- `agent/memory/conversation_store.py`
- `agent/memory/storage.py`
- `bridge/agent_initializer.py`
- `bridge/agent_bridge.py`
- `channel/web/web_channel.py`
- `channel/web/chat.html`
- `channel/web/static/js/console.js`
- `pyproject.toml`

---

## 7. 测试与验证

本次改造不是只写设计和代码，已经完成真实测试验证。

实际通过的测试包括：

- 平台骨架与启动测试
- 多 Agent 隔离测试
- 多租户 / binding 路由测试
- PostgreSQL 主数据、会话、长期记忆索引、任务状态集成测试
- usage / quota / cost 测试
- job API / worker e2e 测试
- audit / doctor / CLI doctor 测试
- Docker compose 校验与真实依赖启动测试
- 测试 / 生产 compose 契约一致性测试
- legacy `app.py` 启动回归测试

本轮 PostgreSQL 迁移后的验证结果：

```bash
COW_PLATFORM_DATABASE_URL=postgresql://... pytest tests/unit tests/integration -q
132 passed, 4 warnings in 5.06s

pytest tests/unit/test_platform_deployment_checks.py \
  tests/e2e/test_platform_deployment_contract.py \
  tests/e2e/test_compose_platform.py -q
5 passed in 0.27s

COW_PLATFORM_DATABASE_URL=postgresql://... pytest \
  tests/e2e/test_compose_base.py \
  tests/e2e/test_platform_deployment_contract.py \
  tests/e2e/test_compose_platform.py \
  tests/e2e/test_platform_health_startup.py \
  tests/e2e/test_platform_real_http_flow.py \
  tests/e2e/test_platform_job_worker_flow.py \
  tests/e2e/test_platform_doctor_cli.py -q
7 passed in 5.91s

PLATFORM_POSTGRES_PASSWORD=... PLATFORM_MINIO_ROOT_USER=... PLATFORM_MINIO_ROOT_PASSWORD=... \
docker compose -p cowagent-prod-smoke \
  -f docker/compose.base.yml \
  -f docker/compose.platform.yml \
  -f docker/compose.prod.yml \
  up -d --build
platform-app / platform-web / postgres / redis 均 healthy，/ready 返回 PostgreSQL / Redis / Qdrant / MinIO 全部 ok

cd channel/web/ui && npm run typecheck && npm run build
passed
```

---

## 8. Reviewer 建议关注点

建议评审重点放在以下方面：

1. 平台层与上游目录的边界是否清晰
2. Agent / tenant / binding 的命名空间隔离是否足够稳妥
3. `AgentBridge` 的 quota 与 usage 接入点是否合理
4. PostgreSQL job claim 与 worker 并发模型是否满足生产部署的异步任务需求
5. `patch-register` 是否足够覆盖未来升级高风险文件

---

## 9. 已知取舍

本 PR 有意识地保留了一些“下一阶段再做”的内容：

- usage token 当前为估算值，不是厂商账单口径
- 外部 IM 渠道平台化主要先打通 Web / binding 模型，其他渠道未做深度运行面改造
- Redis / Qdrant / MinIO 已作为测试和生产一致部署依赖强制校验；当前 job 状态以 PostgreSQL 为强一致来源，Redis Streams 后续用于高吞吐事件分发

这些都是刻意控制复杂度的结果，不是遗漏。

---

## 10. 后续建议

后续建议按以下顺序继续推进：

1. 补齐 app / worker 的观测指标和失败重试策略
2. 逐步把外部渠道接入统一 binding runtime
3. 把 usage 从估算值逐步替换为更精确的模型返回 usage
4. 在任务吞吐成为瓶颈时引入 Redis Streams 作为事件分发层，PostgreSQL 继续作为任务状态来源

---

## 11. 变更总结

这次改造的核心不是“给 CowAgent 再加几个功能”，而是把它从单实例 Agent 引擎，渐进式演进成一个具备：

- 多租户
- 显性多 Agent
- 独立上下文空间
- 渠道绑定
- usage / cost / quota
- 独立 worker
- 审计与自检
- 上游兼容治理

能力的 AI 中台底座。

而且这一步已经不只是设计方案，代码、启动链路、CLI、Docker 和测试都已经真实落地。
