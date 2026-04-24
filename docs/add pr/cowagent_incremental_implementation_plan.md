# CowAgent AI 中台分阶段实施计划

## 1. 计划目标

基于现有 CowAgent 项目，在**不过度设计**的前提下，按阶段把项目从“单实例、单全局配置、单工作区”的 Agent 引擎，逐步演进为：

- 支持显性多 Agent
- 支持多租户隔离
- 支持独立会话 / 记忆 / 梦境 / 知识空间
- 支持渠道绑定
- 支持使用量与成本归因
- 支持 Docker 一键部署
- 保持对上游 CowAgent 的持续兼容能力

本计划默认遵循已有设计文档，但以**当前仓库真实结构**为边界，优先最小侵入落地。

---

## 2. 当前项目现状与约束

结合当前代码，平台化改造的主要约束如下：

1. 配置是全局单例：
   - `config.py` 通过 `load_config()` 和 `conf()` 提供全局配置
2. 运行时依赖大量全局状态：
   - `bridge/bridge.py`
   - `plugins/plugin_manager.py`
   - `agent/memory/conversation_store.py`
   - 多个 channel 的 `@singleton`
3. Agent 工作区是单根目录：
   - `bridge/agent_initializer.py`
   - `agent/prompt/workspace.py`
   - `agent/memory/*`
4. Web 控制台和 CLI 直接读写项目根 `config.json`
5. 当前 Docker 仅面向单应用实例：
   - `docker/docker-compose.yml`
6. 当前自动化测试基础非常薄弱：
   - 只有 `tests/test_minimax_provider.py`

因此，本计划不建议直接在现有 `agent/`、`channel/`、`models/` 下大面积散改，而是优先新增平台层，并通过桥接方式逐步接管运行时。

---

## 3. 实施原则

1. 先建立测试基线，再开始平台化改造
2. 先做单租户显性多 Agent，再扩展到多租户
3. 先打通 Web 控制面和 Web 渠道，再接外部渠道绑定
4. 先做 Direct Cost 统计，不做商业计费
5. 保留 legacy 模式：
   - `app.py`
   - 根 `config.json`
   - 现有 CowAgent Web 控制台
6. 平台新代码统一放入新增的 `platform/` 目录，不把平台业务散落到 upstream 目录

---

## 4. 分阶段实施

## Phase 0：测试基线与平台骨架

### 目标

建立后续改造的最小安全网，不改业务行为。

### 本阶段交付

1. 新增 `platform/` 目录骨架：
   - `platform/domain`
   - `platform/api`
   - `platform/runtime`
   - `platform/repositories`
   - `platform/adapters`
   - `platform/usage`
2. 新增最小公共对象：
   - `RuntimeContext`
   - `AgentDefinition`
   - `SessionState`
   - `PolicySnapshot`
3. 新增测试基础设施：
   - `pytest` 基础配置
   - 单元测试目录
   - 集成测试目录
   - Docker 集成测试目录
4. 新增平台模式最小启动入口：
   - 仅提供 health/readiness 接口
5. 引入 PostgreSQL / Redis / Qdrant / MinIO 的 Docker Compose 基础编排

### 代码落点

- 新增 `platform/`
- 新增 `tests/unit/`
- 新增 `tests/integration/`
- 新增 `tests/e2e/`
- 新增 `docker/compose.base.yml`
- 保持 [app.py](/Users/pusonglin/PycharmProjects/CowAgent-2.0.6/app.py) 不变

### 必做真实测试

1. `RuntimeContext` 构造测试
2. 命名空间生成测试
3. 平台 health API 启动测试
4. Docker Compose 启动 PostgreSQL / Redis / Qdrant / MinIO 成功测试
5. legacy `python app.py` 启动回归测试

### 阶段完成定义

- 不改现有行为
- 新平台入口可启动
- 自动化测试可在本地和 Docker 环境跑通

---

## Phase 1：单租户显性多 Agent

### 目标

在**单租户**前提下，把“一个全局 Agent”改造成“多个显性 Agent 资源”，并完成独立工作区、独立会话、独立记忆、独立知识空间。

### 本阶段交付

1. 新增 `AgentDefinition` 和 `AgentDefinitionVersion` 持久化
2. 平台 API 支持：
   - 创建 Agent
   - 更新 Agent
   - 查询 Agent
3. 新增 `CowAgentRuntimeAdapter`
4. 运行时按 `agent_id` 装配：
   - prompt
   - model config
   - workspace
   - memory namespace
   - knowledge namespace
5. Web 渠道先支持显式指定 Agent
6. 独立工作区目录：
   - `/data/workspaces/{tenant_id}/{agent_id}`
7. 会话改由平台 SessionRepository 管理
8. ConversationStore 统一迁移到 PostgreSQL，不再保留 SQLite 作为运行时存储

### 代码落点

- 新增 `platform/services/agent_service`
- 新增 `platform/runtime/agent_runtime_wrapper`
- 新增 `platform/adapters/cowagent_runtime_adapter`
- 有限改造：
  - [bridge/agent_initializer.py](/Users/pusonglin/PycharmProjects/CowAgent-2.0.6/bridge/agent_initializer.py)
  - [agent/prompt/workspace.py](/Users/pusonglin/PycharmProjects/CowAgent-2.0.6/agent/prompt/workspace.py)
  - [agent/memory/conversation_store.py](/Users/pusonglin/PycharmProjects/CowAgent-2.0.6/agent/memory/conversation_store.py)

### 必做真实测试

1. 创建两个 Agent，验证数据库写入正确
2. 两个 Agent 分别发起对话，验证：
   - session 不串
   - MEMORY.md 不串
   - dream diary 不串
   - knowledge 文件不串
3. 同一用户切换不同 Agent，对话上下文互不影响
4. Web API 指定不同 `agent_id` 时返回不同 persona / 配置结果
5. legacy 模式对话仍可用

### 阶段完成定义

- 单租户下可显式管理多个 Agent
- 每个 Agent 有独立空间
- 平台主链路已不依赖“只有一个 Agent”这一假设

---

## Phase 2：多租户与渠道绑定

### 目标

把单租户显性多 Agent 扩展为多租户，并加入渠道绑定模型。

### 本阶段交付

1. 新增 `Tenant`、`TenantUser`、`ChannelBinding`
2. Resolver 链路落地：
   - TenantResolver
   - UserResolver
   - AgentResolver
   - SessionResolver
3. 所有平台主数据、缓存、工作区、知识、记忆统一带：
   - `tenant_id`
   - `agent_id`
4. 先正式支持：
   - `web`
   - `feishu`
   - `dingtalk`
   - `wecom_bot`
5. 渠道绑定驱动路由：
   - 一个渠道绑定一个 Agent
   - 多个渠道绑定同一个 Agent
6. 默认不做跨渠道共享 Session

### 代码落点

- 新增 `platform/gateway`
- 新增 `platform/resolvers`
- 新增 `platform/adapters/channel_adapter`
- 有限改造：
  - [channel/web/web_channel.py](/Users/pusonglin/PycharmProjects/CowAgent-2.0.6/channel/web/web_channel.py)
  - 各外部 channel 的接入入口

### 必做真实测试

1. 创建两个租户，分别创建同名 Agent，验证数据完全隔离
2. 同一个绑定用户进入不同租户，不得串到错误 Agent
3. 两个渠道绑定同一 Agent，验证长期记忆共享、Session 默认不共享
4. 两个渠道绑定不同 Agent，验证上下文和知识完全隔离
5. 渠道解绑后请求不能再路由到原 Agent

### 阶段完成定义

- 平台正式具备多租户能力
- 渠道已经是绑定入口，不再是业务实体
- Agent 成为真正的一等资源

---

## Phase 3：最小 Usage Metering 与配额治理

### 目标

在不拖慢主链路的前提下，先落地“能看、能追、能聚合”的最小使用量与成本统计。

### 本阶段交付

1. 新增统一 `UsageEvent`
2. 新增三类埋点边界：
   - `ModelGateway`
   - `ToolExecutor`
   - `MCPClientAdapter` 占位接口
3. 主链路只发 usage 事件，不做重聚合
4. worker 消费 usage 事件，写入：
   - `usage_ledger`
   - `tenant_daily_usage`
   - `agent_daily_usage`
5. 成本只做 Direct Cost：
   - token
   - embedding
   - 第三方调用直接成本
6. 新增最小 quota：
   - tenant rpm
   - agent max_steps
   - agent max_context_tokens
   - tool timeout

### 代码落点

- 新增 `platform/usage`
- 新增 `platform/worker`
- 新增 `platform/quota`
- 有限改造：
  - `bridge/agent_bridge.py`
  - `agent/chat/service.py`
  - `agent/protocol/agent_stream.py`

### 必做真实测试

1. 发起一次完整对话，验证 usage_ledger 落库
2. 同一 Agent 多次调用后，验证日聚合正确
3. 两个租户的成本聚合不串
4. tool 调用成功 / 失败都能被计量
5. quota 超限时请求被拒绝，且有正确审计和日志

### 阶段完成定义

- 平台能按租户 / Agent / 会话查看最小成本与用量
- usage 统计对主链路没有明显阻塞

---

## Phase 4：异步执行与 Docker 一键部署

### 目标

把重任务从实时交互里拆出去，并形成开发/测试/生产一致的最小可用部署。

### 本阶段交付

1. app / worker 职责分离
2. PostgreSQL job 表作为第一阶段强一致异步任务状态来源
3. 数据分析类 Agent 支持异步 job
4. Docker Compose 形成生产一致部署栈：
   - platform-app
   - platform-worker
   - platform-web
   - postgres
   - redis
   - qdrant
   - minio
5. PostgreSQL schema 通过 `python -m cow_platform.db.migrate` 幂等初始化
6. 容器启动前通过 `python -m cow_platform.deployment.check --require-all` 校验全依赖
7. CLI 新增平台模式启动命令

### 代码落点

- 新增 `platform/jobs`
- 新增 `docker/compose.platform.yml`
- 新增 `docker/compose.test.yml`
- 新增 `docker/compose.prod.yml`
- 改造 [cli/commands/process.py](/Users/pusonglin/PycharmProjects/CowAgent-2.0.6/cli/commands/process.py)

### 必做真实测试

1. `docker compose up` 后平台全栈可启动
2. migration 自动执行成功
3. 创建异步 job 后 worker 可消费并更新状态
4. app 挂掉后，worker 队列中的任务不丢
5. 本地、测试 Docker 环境执行同一套测试通过

### 阶段完成定义

- 平台具备一键部署能力
- 重任务不再阻塞实时请求

---

## Phase 5：稳定性、回归与上游兼容治理

### 目标

把平台从“能跑”提升到“可持续演进”。

### 本阶段交付

1. Patch Register 文档
2. ADR 文档
3. 上游兼容矩阵
4. 结构化日志字段统一
5. 故障注入测试
6. legacy / platform 双模式回归测试

### 代码落点

- 新增 `docs/adr/`
- 新增 `docs/patch-register.md`
- 新增 `tests/regression/`
- 新增 `tests/fault_injection/`

### 必做真实测试

1. PostgreSQL 不可用时平台失败行为明确
2. Redis 超时时 quota / cache / stream 行为可降级
3. Qdrant 不可用时知识检索可降级
4. MinIO 不可用时 artifact 路径失败可观测
5. 平台模式和 legacy 模式完整回归
6. 拉取上游变更后兼容回归脚本可执行

### 阶段完成定义

- 项目具备长期维护基础
- 平台代码和 CowAgent 内核的边界清晰

---

## 5. 每阶段统一测试要求

每个阶段完成时都必须同时满足：

1. 自动化单元测试通过
2. 自动化集成测试通过
3. 至少 1 条真实端到端链路测试通过
4. 阶段新增的每个公开功能都有独立测试用例
5. legacy 回归通过

测试用例命名建议：

- `tests/unit/platform/...`
- `tests/integration/platform/...`
- `tests/e2e/platform/...`
- `tests/regression/legacy/...`

---

## 6. 不做的事情

为避免过度设计，以下内容不在前四个阶段优先落地：

1. 不做商业计费系统
2. 不做复杂 RBAC 平台
3. 不做 Kubernetes 专属方案
4. 不做完整 MCP 生态集成，只先留边界和埋点
5. 不一次性重写 CowAgent 所有内核模块
6. 不先做复杂管理前端，优先 API 和最小管理能力

---

## 7. 推荐执行顺序

推荐按以下顺序真正开工：

1. Phase 0
2. Phase 1
3. Phase 2
4. Phase 3
5. Phase 4
6. Phase 5

如果中途需要压缩范围，优先保证：

- Phase 0
- Phase 1
- Phase 2
- Phase 3

这四个阶段完成后，平台已经具备最小可用价值。
