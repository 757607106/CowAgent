# 基于 CowAgent 二次开发的 AI 中台总体架构与需求文档

## 1. 文档目的

本文档基于前期沟通内容，对未来基于 CowAgent 进行二次开发的目标、约束、总体架构、核心模块、数据与部署方案、性能与稳定性要求、可维护性治理、成本统计能力、上游兼容策略与实施路线进行统一提炼，作为后续研发评审、拆解任务、技术落地和团队协作的基线文档。

---

## 2. 背景与现状

当前 CowAgent 更适合“单实例、单全局运行时、单套全局配置、多通道接入”的使用形态，适合作为通用 Agent 引擎，但不直接满足以下平台化诉求：

- 单实例多租户
- 显性创建多个 Agent
- 不同租户数据完全隔离
- 不同 Agent 的上下文、记忆、知识、文件空间完全隔离
- 成本按租户 / Agent / 用户 / 会话进行统计
- 保持性能、稳定性、可维护性
- 后续仍能持续吸收 CowAgent 上游更新

因此，本项目不是简单“在 CowAgent 上叠功能”，而是要将其演进为：

**一个以 CowAgent 为可升级内核、具备多租户、显性 Agent、成本计量、治理与可维护性的 AI 中台。**

---

## 3. 项目目标

### 3.1 总体目标

构建一个基于 CowAgent 的 AI 中台，满足：

1. 单实例多租户
2. 支持显性创建多个 Agent
3. 租户间数据完全隔离
4. Agent 间上下文空间完全隔离
5. 支持多种 Agent 类型（如售后客服、数据分析 Agent）
6. 具备成本统计与资源治理能力
7. 具备高性能、稳定性与可维护性
8. 支持 Docker 一键部署
9. 开发、测试、生产环境保持一致
10. 后续可持续吸收 CowAgent 上游更新

### 3.2 非目标

本期不追求：

- 每个租户独立一套服务实例
- 一次性重写 CowAgent 全部内部实现
- 第一阶段就引入极重的微服务体系
- 第一阶段就实现完整商业计费系统
- 第一阶段就实现全部精细化资源摊销

---

## 4. 需求提炼

## 4.1 已确认核心需求

### 功能需求

1. 基于 CowAgent 进行二次开发
2. 支持单实例多租户
3. 不同租户数据完全隔离
4. 支持显性创建多个 Agent
5. 支持不同类型 Agent，例如：
   - 售后客服 Agent
   - 数据分析 Agent
6. 不同 Agent 的上下文、记忆、知识和会话完全隔离
7. 支持知识库、长期记忆、工具、Skill 等能力与 Agent 绑定
8. 支持租户、Agent、会话级别的治理与管理

### 非功能需求

9. 性能可控
10. 稳定
11. 可维护
12. 逻辑清晰
13. 支持后续吸收 CowAgent 上游功能更新
14. 支持 AI 中台级别的成本统计
15. 支持统计：
   - token 使用量
   - tool 调用次数
   - MCP 调用次数
   - 成本归因
16. 成本统计不能明显影响主链路性能
17. 需要明确数据库和存储选型
18. 支持 Docker 一键部署
19. 开发、测试、生产环境依赖保持一致
20. 数据库开发与生产均使用 Docker，不允许测试和生产数据库类型不一致

---

## 5. 架构设计原则

### 5.1 显式上下文优于隐式状态

任何执行链路必须显式携带：

- tenant_id
- agent_id
- user_id
- session_id
- request_id
- policy_snapshot
- workspace_path

禁止依赖“当前全局 tenant / agent / session”。

### 5.2 控制面与运行面分离

- 控制面：定义系统“长什么样”
- 运行面：定义一次请求“怎么跑”

### 5.3 平台层与 CowAgent 内核解耦

- 多租户、显性 Agent、配额、审计、成本统计等平台能力放在平台层
- 对 CowAgent 的接入通过桥接层完成
- CowAgent 内核尽量少改，保持接近 upstream

### 5.4 共享底座，隔离命名空间

单实例下共享：

- 应用进程
- 数据库集群
- Redis
- 向量库
- 对象存储
- 模型网关

但所有数据、缓存、检索和工作区都必须严格带租户 / Agent 命名空间。

### 5.5 主链路轻量，异步链路承载重任务

- 交互请求优先低延迟
- 成本统计、聚合、异步任务、重工具调用走异步链路

### 5.6 平台机制优先

隔离、限流、配额、缓存、审计、成本统计、降级、灰度等必须是统一机制，不允许散落在业务 if/else 中。

---

## 6. 总体架构

## 6.1 分层架构

```text
Client / Channel
   -> Gateway
      -> TenantResolver
      -> AgentResolver
      -> SessionResolver
      -> Auth / Quota / RateLimit
      -> RuntimeDispatcher
           -> AgentRuntime Wrapper
                -> Context Assembler
                -> Memory Service
                -> Knowledge Service
                -> Tool Orchestrator
                -> MCP Client
                -> Model Gateway
                -> Response Composer
                -> Usage Accumulator / Event Emitter

Control Plane
   -> Tenant Service
   -> Agent Service
   -> Binding Service
   -> Policy Service
   -> Quota Service
   -> Admin API / Console

Bridge Layer
   -> ConfigMapper
   -> CowAgent Runtime Adapter
   -> Tool Adapter
   -> Skill Adapter
   -> Channel Adapter
   -> Model Adapter

CowAgent Kernel
   -> Upstream agent/channel/models/tools/skills capabilities

Infra Layer
   -> PostgreSQL
   -> Redis
   -> Qdrant
   -> MinIO
   -> Worker
   -> Queue / Stream
   -> Sandbox Executor
   -> Observability
```

## 6.2 三层职责划分

### A. Platform Layer

负责平台能力：

- 多租户
- 显性 Agent
- Session 管理
- Quota
- Audit
- Usage Metering
- Cost Accounting
- Gateway
- Admin API

### B. Bridge Layer

负责适配 CowAgent：

- 将平台对象映射为 CowAgent 可消费的运行配置
- 包装 CowAgent runtime / tool / skill / model / channel 能力
- 吸收 upstream 变化

### C. CowAgent Kernel

尽量保持接近上游，作为可升级内核。

---

## 7. 核心领域模型

## 7.1 Tenant

租户，是最高隔离边界。

### 作用
- 数据归属主体
- Quota / Cost / Policy 主体
- Agent 容器

## 7.2 TenantUser

租户内用户，可映射多个渠道身份。

## 7.3 AgentDefinition

显性 Agent 定义，是平台中的一等资源对象。

### 内容
- 名称
- profile_type
- system_prompt
- model_config
- context_policy
- memory_policy
- tool_policy
- skill_policy
- knowledge_bindings
- quota_policy
- version
- status

## 7.4 Session

一次会话执行实例，可为对话型，也可扩展为任务型。

## 7.5 KnowledgeSpace

知识空间，可绑定给一个或多个 Agent。

## 7.6 MemorySpace

长期记忆空间，建议以 `tenant + agent` 为主命名空间。

## 7.7 ChannelBinding

外部 channel 与 tenant / agent 的绑定关系。

## 7.8 Policy

统一策略层，至少包括：

- ToolPolicy
- SkillPolicy
- ContextPolicy
- QuotaPolicy
- SafetyPolicy

---

## 8. 核心运行时对象

## 8.1 RuntimeContext

```python
@dataclass(frozen=True)
class RuntimeContext:
    request_id: str
    tenant_id: str
    user_id: str
    agent_id: str
    session_id: str
    channel_type: str
    channel_user_id: str
    workspace_path: str
    memory_ns: str
    knowledge_ns: str
    cache_ns: str
    policy_snapshot: PolicySnapshot
```

### 作用

- 全链路显式上下文
- 日志统一维度
- cache / quota / audit / usage 统一维度
- 隔离与排障的基础

## 8.2 AgentDefinition

```python
@dataclass
class AgentDefinition:
    tenant_id: str
    agent_id: str
    name: str
    profile_type: str
    description: str
    system_prompt: str
    model_config: dict
    context_policy: dict
    memory_policy: dict
    tool_policy: dict
    skill_policy: dict
    knowledge_bindings: list[str]
    quota_policy: dict
    version: int
    status: str
```

## 8.3 SessionState

```python
@dataclass
class SessionState:
    tenant_id: str
    agent_id: str
    session_id: str
    user_id: str
    recent_messages: list
    summary: str | None
    tool_trace: list
    artifacts: list
    status: str
```

## 8.4 PolicySnapshot

```python
@dataclass(frozen=True)
class PolicySnapshot:
    tool_policy: dict
    skill_policy: dict
    context_policy: dict
    quota_policy: dict
    safety_policy: dict
```

---

## 9. 多租户与 Agent 隔离设计

## 9.1 隔离目标

必须同时做到：

1. 控制面隔离
2. 数据面隔离
3. 执行面隔离

## 9.2 命名空间规范

建议统一：

```text
tenant_ns  = tenant:{tenant_id}
agent_ns   = tenant:{tenant_id}:agent:{agent_id}
session_ns = tenant:{tenant_id}:agent:{agent_id}:session:{session_id}
user_ns    = tenant:{tenant_id}:user:{user_id}
```

## 9.3 数据隔离范围

### 必须按 tenant / agent 隔离的数据包括：

- 会话上下文
- 长期记忆
- 知识检索范围
- 工具执行痕迹
- MCP 调用痕迹
- usage 与成本账本
- 文件工作区
- artifact
- cache
- quota
- 审计日志

## 9.4 工作区规范

```text
/workspaces/{tenant_id}/{agent_id}/
/tmp/{tenant_id}/{agent_id}/{session_id}/
/artifacts/{tenant_id}/{agent_id}/
```

---

## 10. 显性 Agent 设计

## 10.1 为什么必须显性化

当前 CowAgent 的思路更偏“agent 功能开关 + 单套全局配置”，不适合企业中台下多个 Agent 并存与管理。

显性 Agent 化后，Agent 不再是抽象能力，而是平台中的一等资源对象。

## 10.2 Agent 能力维度

每个 Agent 可独立配置：

- Prompt
- 模型
- 工具
- Skill
- 知识库
- 记忆策略
- 上下文策略
- Quota
- 安全策略

## 10.3 Agent Profile

第一期建议仅支持三类：

- customer_service
- data_analyst
- general_assistant

### customer_service

特点：

- 低延迟
- 强检索
- 弱自主规划
- 工具白名单严格
- 适用于售后客服、FAQ、知识问答

### data_analyst

特点：

- 可异步任务化
- 可启用 Python / SQL / 文件处理
- 更强工具能力
- 独立 workspace
- 长任务与 artifact 管理

### general_assistant

特点：

- 通用中性配置
- 适合办公问答与轻任务

---

## 11. 控制面设计

控制面负责平台资源管理，而不是实时对话处理。

## 11.1 控制面职责

- Tenant CRUD
- TenantUser 管理
- Agent CRUD
- Agent 版本管理
- Binding 管理
- Policy 管理
- Quota 管理
- KnowledgeSpace 管理
- Agent 绑定知识空间
- 工具和 Skill 启用关系
- 成本与用量查看
- 灰度与回滚

## 11.2 控制面 API 示例

- `POST /tenants`
- `POST /tenants/{tenant_id}/agents`
- `PUT /tenants/{tenant_id}/agents/{agent_id}`
- `POST /bindings`
- `GET /tenants/{tenant_id}/usage`
- `GET /tenants/{tenant_id}/costs`
- `GET /tenants/{tenant_id}/agents/{agent_id}/usage`
- `POST /tenants/{tenant_id}/agents/{agent_id}/rollback`

---

## 12. Gateway 与运行时链路

## 12.1 主链路

```text
Channel Event
 -> ChannelAdapter.normalize()
 -> MessageGateway.handle()
 -> TenantResolver.resolve()
 -> UserResolver.resolve()
 -> AgentResolver.resolve()
 -> SessionResolver.resolve()
 -> RuntimeContextFactory.build()
 -> AgentFactory.create_runtime()
 -> AgentRuntimeWrapper.handle()
 -> ChannelAdapter.reply()
```

## 12.2 AgentRuntimeWrapper 逻辑

```text
load definition
 -> load session state
 -> assemble context
 -> retrieve memory
 -> retrieve knowledge
 -> decide tools / MCP
 -> call model
 -> accumulate usage
 -> persist session summary
 -> emit usage events
 -> reply
```

---

## 13. 性能设计

## 13.1 核心目标

必须同时满足：

- 实时交互型 Agent 低延迟
- 任务型 Agent 不阻塞交互请求
- 成本统计不影响主链路
- 多租户流量可治理
- 不同 Agent 类型互不拖垮

## 13.2 流量分型

### 实时交互流量

适用：

- 售后客服
- 知识问答
- 轻量办公问答

目标：

- 低延迟
- 小上下文
- 少步数
- 强缓存

### 后台任务流量

适用：

- 数据分析
- 文件处理
- 报表生成
- 浏览器 / Python / SQL 重任务

目标：

- 异步化
- 可排队
- 可恢复
- 不阻塞主链路

### 控制面流量

适用：

- 创建租户
- 创建 Agent
- 改配置
- 查报表

目标：

- 高可靠
- 低频
- 强一致

## 13.3 上下文优化

不能每次把全量历史塞给模型。

建议每次仅注入：

1. Agent 固定指令
2. 最近 N 轮短上下文
3. 检索出的相关长期记忆
4. 检索出的相关知识片段

旧轮次做 summary。

## 13.4 运行时缓存

### Agent Runtime Cache

缓存：

- AgentDefinition 编译结果
- 模型客户端
- 工具注册表
- Skill 描述
- 知识绑定元数据

### Retrieval Cache

缓存：

- 热门知识查询结果
- 记忆召回结果
- 同会话内高频 query

## 13.5 资源池拆分

必须拆分：

- app runtime pool
- worker pool
- python worker pool
- browser worker pool
- file worker pool

## 13.6 Quota

### TenantQuota

- max_concurrent_sessions
- max_requests_per_minute
- max_tokens_per_day
- max_async_jobs
- max_storage_mb

### AgentQuota

- max_concurrent_runs
- max_steps_per_run
- max_tool_calls_per_run
- max_context_tokens

### ToolQuota

- max_parallel_executions
- timeout_seconds
- max_file_size_mb

---

## 14. 稳定性设计

## 14.1 外部能力统一 Adapter 化

必须统一抽象：

- ModelGateway
- ToolExecutor
- MCPClient
- StorageAdapter
- VectorStoreAdapter
- QueueAdapter
- SandboxExecutorAdapter

## 14.2 失败策略

### 模型调用

- timeout
- limited retry
- fallback model
- circuit breaker

### 检索

- timeout 后降级
- 必要时可跳过检索继续保守回答

### 工具 / MCP

- timeout
- 审计
- 失败摘要
- 严禁无限重试

### Session 持久化

- fail fast 或降级为短期临时会话
- 不允许不透明失败

## 14.3 幂等性

以下必须幂等：

- 创建 session
- 创建 job
- 写 usage ledger
- 写 audit
- 回写 tool/MCP 结果
- channel 回复状态更新

## 14.4 降级策略

平台必须支持：

- 历史窗口缩短
- 检索 TopK 降低
- 大模型降级为中模型
- 禁用高风险工具
- 重任务转异步
- 某些 Agent 只读模式

---

## 15. 可维护性设计

## 15.1 设计目标

保证：

- 逻辑清晰
- 边界明确
- 新需求改动集中
- 上游升级可控
- 团队协作不失控

## 15.2 三层维护策略

### Platform Layer

放平台业务逻辑：

- tenant
- agent
- session
- gateway
- quota
- usage
- audit

### Bridge Layer

放 CowAgent 适配逻辑：

- config mapper
- runtime adapter
- tool adapter
- skill adapter
- channel adapter
- model adapter

### CowAgent Kernel

尽量少改，保持接近 upstream。

## 15.3 开发规约

1. 新需求必须先回答“属于哪一层”
2. 禁止业务逻辑依赖全局状态
3. 禁止绕过 repository / adapter 访问底层
4. 禁止在 channel、tool、skill 内散落租户特例
5. 修改 CowAgent 原文件必须登记 patch register
6. 所有核心 public service 必须有结构化日志
7. 所有外部调用必须带 timeout

## 15.4 Patch Register

所有对上游原文件的改动都必须登记：

- 文件
- 改动原因
- 为什么不能通过 bridge 解决
- 升级关注点
- 负责人

## 15.5 ADR

建议建立 Architecture Decision Record，记录关键决策，例如：

- 采用 RuntimeContext
- Gateway 统一路由
- ToolExecutor 统一埋点与权限控制
- 使用 Qdrant 作为向量库
- 使用 Redis Streams 作为第一阶段异步事件通道
- Upstream 兼容策略

---

## 16. 上游 CowAgent 兼容策略

## 16.1 目标

二开后仍要尽量持续吸收 CowAgent upstream 更新。

## 16.2 核心策略

### 1. CowAgent 视为可升级内核

而不是业务代码容器。

### 2. 平台能力不直接揉进 CowAgent 各目录

避免在：

- agent
- channel
- models
- plugins
- skills
- app.py
- config.py

中大面积散改。

### 3. 通过 Bridge Layer 适配上游变化

上游变化优先通过：

- ConfigMapper
- RuntimeAdapter
- ToolAdapter
- SkillAdapter
- ChannelAdapter
- ModelAdapter

吸收。

## 16.3 升级流程

1. 拉取 upstream
2. 识别变化类型
3. 优先修改 bridge layer
4. 运行兼容测试
5. 小流量灰度
6. 更新兼容矩阵

## 16.4 兼容矩阵

建议维护：

```text
Platform Version   CowAgent Version   Status
v1.0               2.0.x              stable
v1.1               2.1.x              testing
```

---

## 17. Usage Metering 与成本统计设计

## 17.1 目标

作为 AI 中台，必须能够回答：

- 每个租户花了多少 token
- 每个 Agent 花了多少 token
- 每个用户 / 会话消耗了多少
- 调用了多少次 tool
- 调用了多少次 MCP
- 每类模型成本是多少
- 哪些租户 / Agent 成本异常增长

且统计不能明显影响性能。

## 17.2 统计对象

至少覆盖：

- llm_call
- tool_call
- mcp_call
- retrieval_call
- embedding_call
- storage_read
- storage_write
- artifact_create

## 17.3 统一 UsageEvent

```python
@dataclass(frozen=True)
class UsageEvent:
    event_id: str
    event_type: str
    timestamp: datetime

    tenant_id: str
    agent_id: str
    user_id: str | None
    session_id: str | None
    request_id: str | None
    job_id: str | None

    provider: str | None
    resource_name: str | None
    status: str

    input_units: int | None
    output_units: int | None
    latency_ms: int | None

    raw_cost: Decimal | None
    currency: str | None

    metadata: dict
```

## 17.4 主链路与异步链路分离

主链路只做：

1. 采集原始 usage 数据
2. 发出轻量 usage event

异步链路负责：

- usage ledger 写入
- pricing 计算
- 聚合统计
- 成本报表
- 告警

## 17.5 双轨统计模型

### Usage Ledger（明细账本）

作用：

- 审计
- 追账
- 对账
- 重算成本

### Usage Aggregate（聚合统计）

作用：

- 控制台展示
- 成本趋势
- 配额和告警

## 17.6 计量边界层

### ModelGateway

统一统计：

- provider
- model_name
- input_tokens
- output_tokens
- cached/reasoning tokens（如有）
- latency
- cost

### ToolExecutor

统一统计：

- tool_name
- status
- latency
- call_count
- artifact_count

### MCPClient

统一统计：

- mcp_server_name
- method
- request_size
- response_size
- status
- latency

## 17.7 RequestUsageSummary

每次请求结束时再生成一次轻量请求汇总，便于：

- 请求级追账
- 平均请求成本分析
- 问题排查

## 17.8 成本维度

建议分三层：

### Direct Cost

- LLM token
- embedding
- 第三方 MCP/API 按量成本

### Execution Cost

- worker CPU 时间
- 文件处理
- 浏览器任务
- 工具执行占用

### Allocated Cost

- 平台固定资源摊销

### 第一阶段建议

先做准 Direct Cost，Execution Cost 和 Allocated Cost 后续再补。

---

## 18. 数据库与中间件选型

## 18.1 选型目标

满足：

- Docker 一键部署
- 开发/测试/生产一致
- 多租户隔离
- 成本统计
- 性能可控
- 可维护

## 18.2 推荐选型

### PostgreSQL

用作主业务数据库，存：

- tenant
- tenant_user
- agent_definition
- channel_binding
- session 元数据
- policy
- quota
- pricing catalog
- usage 聚合
- job 元数据
- audit 索引

### Redis

用作：

- 热状态
- session cache
- rate limit
- quota counter
- runtime cache
- retrieval cache
- stream / lightweight queue

### Qdrant

用作：

- knowledge vector
- memory vector
- embedding index

### MinIO

用作：

- 文件
- artifact
- 原始文档
- 分析结果
- 导出文件

## 18.3 第一阶段不强制引入

- ClickHouse
- Kafka
- RabbitMQ

理由：

第一阶段先保证简单、稳定、Docker 一致部署。随着 usage 明细和异步量上来，再扩展。

---

## 19. 数据存储职责分工

## 19.1 PostgreSQL

负责：

- 强一致元数据
- 业务配置
- 关系型查询
- usage 聚合表
- 成本统计结果
- pricing catalog

## 19.2 Redis

负责：

- 热 session
- cache
- 限流与配额计数
- event buffer / streams
- request 级短期聚合

## 19.3 Qdrant

负责：

- 知识检索
- 长期记忆召回
- embedding 向量

## 19.4 MinIO

负责：

- 大文件
- artifact
- 上传文档
- 报告与导出结果

---

## 20. 主要表设计建议

## 20.1 主业务表

- tenants
- tenant_users
- agent_definitions
- channel_bindings
- sessions
- knowledge_spaces
- agent_knowledge_bindings
- jobs
- pricing_catalog

## 20.2 Usage 表

### usage_ledger

明细账本，append-only。

### tenant_daily_usage

租户日聚合。

### agent_daily_usage

Agent 日聚合。

### tenant_model_daily_usage

按模型维度聚合。

### tenant_tool_daily_usage

按工具维度聚合。

### tenant_mcp_daily_usage

按 MCP 维度聚合。

---

## 21. Docker 一键部署与环境一致性设计

## 21.1 硬约束

开发、测试、预发、生产必须保持同一套技术栈和核心依赖。

不能出现：

- 开发用 SQLite，生产用 PostgreSQL
- 开发不用 Redis，生产才用 Redis
- 测试用本地文件，生产用对象存储
- 测试不用向量库，生产才接 Qdrant

## 21.2 环境一致性原则

一致内容包括：

- 服务种类
- 数据库类型
- Docker 镜像
- migration 机制
- 启动方式
- 健康检查思路

不同环境只允许变更：

- 配置
- 资源规格
- 副本数
- 安全策略
- 数据卷路径

## 21.3 建议部署组件

### 最小可用版

- app
- worker
- postgres
- redis
- qdrant
- minio

### 标准版

- app
- worker
- postgres
- redis
- qdrant
- minio
- nginx
- migrate/init-job

## 21.4 Compose 组织建议

```text
docker/
  compose.base.yml
  compose.dev.yml
  compose.test.yml
  compose.prod.yml
  env/
    dev.env
    test.env
    prod.env
```

## 21.5 migration 原则

开发、测试、生产统一使用同一套 migration 工具和 schema 版本管理。

禁止：

- 手工改生产表结构
- 测试环境使用不同 schema
- 开发环境绕过 migration

---

## 22. 部署形态建议

## 22.1 应用拆分

### app

职责：

- API
- Gateway
- Control Plane
- Runtime Orchestration
- 实时请求处理

### worker

职责：

- 重工具任务
- usage aggregation
- embedding pipeline
- 文件处理
- 长任务
- 异步 job

## 22.2 单机与生产一致策略

即使生产未来进入 Kubernetes，第一阶段仍建议：

- 开发用 Docker Compose
- 测试用 Docker Compose 或兼容的编排方式
- 生产小规模也可以 Docker Compose
- 重点保证镜像与依赖一致

---

## 23. 测试策略

## 23.1 测试层次

### 单元测试

重点测：

- resolver
- policy
- quota
- context assemble
- session summary
- config mapper
- cache key builder

### 契约测试

重点测：

- AgentRepository
- SessionRepository
- ModelGateway
- ToolExecutor
- MCPClient
- SkillLoader

### 集成测试

覆盖：

- 单租户单 Agent
- 单租户多 Agent
- 多租户隔离
- tool policy
- MCP usage
- 成本统计链路
- usage 归因是否正确

### 回归测试

重点支持 upstream 升级与版本切换。

### 故障注入测试

模拟：

- Redis 超时
- PG 连接失败
- Qdrant 失败
- MinIO 失败
- 模型 429/500
- worker 崩溃

---

## 24. 可观测性设计

## 24.1 日志字段

所有核心日志至少带：

- request_id
- tenant_id
- agent_id
- session_id
- job_id
- operation
- component
- latency_ms
- status
- error_code

## 24.2 Trace 贯通

至少贯穿：

- Gateway
- AgentRuntime
- Memory / Knowledge Search
- Model Call
- Tool Call
- MCP Call
- Session Persist
- Usage Event Emit
- Channel Reply

## 24.3 审计日志

必须可追踪：

- 谁调用了哪个 Agent
- 调了哪个模型
- 用了哪些 tool / MCP
- 生成了哪些 artifact
- 花了多少 token 和成本

---

## 25. 安全与权限

## 25.1 多租户权限边界

必须明确：

- 平台管理员
- 租户管理员
- 租户普通用户

## 25.2 Agent 能力权限

通过 Policy 管理：

- 可用模型
- 可用工具
- 可用 MCP server
- 可用 Skill
- 可访问知识空间
- 可读写文件范围

## 25.3 高风险能力默认关闭

例如：

- shell
- browser
- unrestricted file write
- arbitrary code execution

只对特定 Agent Profile 或特定租户开放。

---

## 26. 维护性治理要求

## 26.1 红线

1. 禁止在 channel 中写租户 / Agent 业务逻辑
2. 禁止在 tool / skill 内散落 tenant 特例
3. 禁止新增业务全局单例
4. 禁止业务层直接使用底层 SDK
5. 禁止无 patch register 修改 CowAgent 原文件
6. 禁止无测试合并 bridge / runtime_ext 关键改动

## 26.2 Code Review 检查项

每个 PR 必须检查：

- 需求属于哪一层
- 是否越层
- 是否引入全局状态
- 是否修改 upstream 原文件
- patch 是否登记
- 是否影响隔离
- 是否影响 usage 和成本归因
- 是否补测试
- 是否有回滚方案

---

## 27. 实施路线

## Phase 1：平台骨架

目标：

- RuntimeContext
- AgentDefinition
- SessionState
- Gateway / Resolver
- Repository / Adapter 接口
- 最小单租户多 Agent 能力

## Phase 2：多租户与隔离

目标：

- Tenant / TenantUser / Binding
- 命名空间化
- Workspace / Cache / Retrieval 隔离
- Usage 归因维度完整化

## Phase 3：性能与异步执行

目标：

- app / worker 拆分
- Retrieval Cache
- Runtime Cache
- Async Job
- Tool/MCP 异步执行框架

## Phase 4：Usage Metering 与成本统计

目标：

- Model / Tool / MCP 统一埋点
- Usage Ledger
- 聚合统计
- 控制台报表
- Quota / 告警

## Phase 5：稳定性与治理

目标：

- Audit
- Trace
- Fault Injection
- 灰度
- 版本回滚
- 上游兼容机制

---

## 28. 关键风险与应对

## 风险 1：直接魔改 CowAgent 原目录导致后续难以升级

### 应对
- 平台层 / bridge 层优先
- 核心 patch 点登记
- 控制侵入点数量

## 风险 2：主链路被重工具、统计、聚合拖慢

### 应对
- app / worker 分离
- usage 事件异步化
- request summary + ledger 双轨

## 风险 3：租户或 Agent 串数据

### 应对
- RuntimeContext 全链路显式
- 命名空间严格统一
- repository 层强制 tenant / agent 过滤

## 风险 4：开发/测试/生产环境漂移

### 应对
- 全部依赖 Docker 化
- 不允许替代数据库类型
- 统一 migration 和 compose 体系

## 风险 5：团队开发导致结构退化

### 应对
- Code Review 清单
- ADR
- Patch Register
- 明确目录边界与红线

---

## 29. 当前推荐技术栈

### 应用
- Python 应用服务（app）
- Python worker

### 数据与中间件
- PostgreSQL
- Redis
- Qdrant
- MinIO

### 第一阶段消息通道
- Redis Streams

### 后续扩展候选
- ClickHouse（大规模 usage 分析）
- RabbitMQ / Kafka（更大规模异步队列）

---

## 30. 最终结论

本项目的正确方向不是“继续在 CowAgent 的单实例逻辑上叠补丁”，而是：

**将 CowAgent 作为可升级内核，在其上构建一层具备多租户、显性 Agent、强隔离、成本统计、治理与可维护性的 AI 中台平台层。**

最终需要达成的核心状态是：

1. 单实例多租户  
2. 不同租户数据完全隔离  
3. 显性创建多个 Agent  
4. 不同 Agent 的上下文、记忆、知识完全隔离  
5. 使用量与成本可按租户 / Agent / 用户 / 会话归因  
6. 成本统计不显著影响性能  
7. 开发、测试、生产环境依赖一致  
8. 通过 Docker 一键部署  
9. 可维护、稳定、逻辑清晰  
10. 后续能持续吸收 CowAgent 上游更新  

---

## 31. 建议后续输出物

建议基于本文档继续落地以下研发文档：

1. 《核心类图与时序图设计》
2. 《数据库表结构设计》
3. 《Usage Metering 事件与聚合设计》
4. 《Docker Compose 一键部署设计》
5. 《Code Review 规范与 Patch Register 模板》
6. 《Upstream 升级 SOP 与兼容矩阵》
7. 《测试计划与回归用例集》
