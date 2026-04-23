# 核心模块类图与时序图设计文档

## 1. 目标

本文档给出平台关键模块、核心对象、接口设计与关键链路时序，作为研发拆任务与代码落地的直接参考。

---

## 2. 模块分层

```text
platform/
  control_plane/
  gateway/
  runtime_ext/
  domain/
  capabilities/
  bridge/
  infra/
  tests/
```

---

## 3. 核心类图（文本版）

```text
TenantService
  ├─ TenantRepository
  └─ AuditService

AgentService
  ├─ AgentRepository
  ├─ KnowledgeBindingRepository
  └─ VersioningService

MessageGateway
  ├─ TenantResolver
  ├─ UserResolver
  ├─ AgentResolver
  ├─ SessionResolver
  ├─ AuthGuard
  ├─ RateLimitGuard
  ├─ QuotaGuard
  └─ RuntimeDispatcher

RuntimeDispatcher
  └─ AgentFactory

AgentFactory
  ├─ AgentRepository
  ├─ ConfigMapper
  ├─ ModelGatewayFactory
  ├─ MemoryFactory
  ├─ KnowledgeFactory
  ├─ ToolFactory
  └─ SkillLoader

AgentRuntimeWrapper
  ├─ SessionManager
  ├─ ContextAssembler
  ├─ MemoryService
  ├─ KnowledgeService
  ├─ ToolOrchestrator
  ├─ MCPClient
  ├─ ModelGateway
  ├─ ResponseComposer
  ├─ RequestUsageAccumulator
  └─ UsageEventEmitter
```

---

## 4. 关键对象定义

## 4.1 RuntimeContext

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

## 4.2 AgentDefinition

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

## 4.3 SessionState

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

## 4.4 UsageEvent

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

---

## 5. 核心接口定义

## 5.1 Repository

```python
class AgentRepository(Protocol):
    def get(self, tenant_id: str, agent_id: str) -> AgentDefinition: ...
    def save(self, definition: AgentDefinition) -> None: ...
```

```python
class SessionRepository(Protocol):
    def load(self, tenant_id: str, agent_id: str, session_id: str) -> SessionState | None: ...
    def save(self, session: SessionState) -> None: ...
```

```python
class TenantRepository(Protocol):
    def get(self, tenant_id: str) -> Tenant: ...
```

## 5.2 Capability Interfaces

```python
class ModelGateway(Protocol):
    def generate(self, ctx: RuntimeContext, prompt: PromptPackage) -> ModelResponse: ...
```

```python
class ToolExecutor(Protocol):
    def execute(self, ctx: RuntimeContext, tool_name: str, args: dict) -> ToolResult: ...
```

```python
class MCPClient(Protocol):
    def call(self, ctx: RuntimeContext, server_name: str, method: str, payload: dict) -> MCPResult: ...
```

```python
class KnowledgeRepository(Protocol):
    def search(self, ctx: RuntimeContext, query: str, top_k: int) -> list[KnowledgeChunk]: ...
```

```python
class MemoryRepository(Protocol):
    def load_relevant(self, ctx: RuntimeContext, query: str) -> list[MemoryChunk]: ...
    def append_turn(self, ctx: RuntimeContext, turn: MessageTurn) -> None: ...
```

```python
class UsageEventEmitter(Protocol):
    def emit(self, event: UsageEvent) -> None: ...
    def emit_batch(self, events: list[UsageEvent]) -> None: ...
```

---

## 6. AgentFactory 装配伪代码

```python
class AgentFactory:
    def create_runtime(self, ctx: RuntimeContext) -> "AgentRuntimeWrapper":
        definition = self.agent_repo.get(ctx.tenant_id, ctx.agent_id)

        model = self.model_gateway_factory.create(definition.model_config)
        memory = self.memory_factory.create(ctx, definition.memory_policy)
        knowledge = self.knowledge_factory.create(ctx, definition.knowledge_bindings)
        tools = self.tool_factory.create(ctx, definition.tool_policy)
        skills = self.skill_loader.load_enabled_skills(ctx)

        return AgentRuntimeWrapper(
            ctx=ctx,
            definition=definition,
            model=model,
            memory=memory,
            knowledge=knowledge,
            tools=tools,
            skills=skills,
            session_manager=self.session_manager,
            usage_accumulator=self.usage_accumulator_factory.create(ctx),
            usage_event_emitter=self.usage_event_emitter,
        )
```

---

## 7. 主消息链路时序图（文本版）

```text
User/Channel
 -> ChannelAdapter.normalize()
 -> MessageGateway.handle(envelope)
 -> TenantResolver.resolve(envelope)
 -> UserResolver.resolve(envelope)
 -> AgentResolver.resolve(envelope)
 -> SessionResolver.resolve(envelope)
 -> RuntimeContextFactory.build(...)
 -> RuntimeDispatcher.dispatch(ctx, message)
 -> AgentFactory.create_runtime(ctx)
 -> AgentRuntimeWrapper.handle(message)
 -> ChannelAdapter.reply(result)
```

---

## 8. AgentRuntimeWrapper 时序图（文本版）

```text
AgentRuntimeWrapper.handle(message)
  -> SessionManager.load(ctx)
  -> ContextAssembler.build(ctx, session, message)
  -> MemoryService.load_relevant(ctx, query)
  -> KnowledgeService.search(ctx, query)
  -> Planner/Decision (optional)
  -> ToolOrchestrator / MCPClient (optional)
  -> ModelGateway.generate(ctx, prompt)
  -> RequestUsageAccumulator.record(...)
  -> SessionManager.save(ctx, new_state)
  -> UsageEventEmitter.emit_batch(...)
  -> ResponseComposer.compose(...)
  -> return response
```

---

## 9. 数据分析 Agent 异步任务时序

```text
User Request
 -> Gateway
 -> AgentRuntimeWrapper
 -> Planner determines long-running job
 -> JobService.create_job(...)
 -> QueueAdapter.publish(job_event)
 -> return accepted / task created

Worker
 -> QueueAdapter.consume(job_event)
 -> load job
 -> ToolExecutor / MCPClient / Python sandbox
 -> persist artifacts
 -> emit usage events
 -> update job status
```

---

## 10. Usage Metering 时序

```text
ModelGateway.generate()
 -> receive provider usage
 -> RequestUsageAccumulator.record_llm(...)
 -> UsageEventEmitter.emit(UsageEvent[type=llm_call])

ToolExecutor.execute()
 -> measure latency/status
 -> RequestUsageAccumulator.record_tool(...)
 -> UsageEventEmitter.emit(UsageEvent[type=tool_call])

MCPClient.call()
 -> measure latency/status
 -> RequestUsageAccumulator.record_mcp(...)
 -> UsageEventEmitter.emit(UsageEvent[type=mcp_call])

Request ends
 -> RequestUsageAccumulator.to_summary()
 -> UsageEventEmitter.emit(RequestSummaryEvent)
```

---

## 11. Gateway 关键守卫顺序

建议顺序：

1. AuthGuard
2. TenantResolver
3. UserResolver
4. AgentResolver
5. SessionResolver
6. RateLimitGuard
7. QuotaGuard
8. RuntimeDispatcher

---

## 12. RequestUsageAccumulator 伪代码

```python
class RequestUsageAccumulator:
    def __init__(self, ctx: RuntimeContext):
        self.ctx = ctx
        self.llm_calls = 0
        self.llm_input_tokens = 0
        self.llm_output_tokens = 0
        self.llm_cost = Decimal("0")
        self.tool_calls = 0
        self.mcp_calls = 0
        self.retrieval_calls = 0
        self.events = []

    def record_llm(self, provider, model_name, input_tokens, output_tokens, cost, latency_ms, status):
        self.llm_calls += 1
        self.llm_input_tokens += input_tokens or 0
        self.llm_output_tokens += output_tokens or 0
        self.llm_cost += cost or Decimal("0")
        self.events.append(...)

    def record_tool(self, tool_name, latency_ms, status):
        self.tool_calls += 1
        self.events.append(...)

    def record_mcp(self, server_name, method, latency_ms, status):
        self.mcp_calls += 1
        self.events.append(...)

    def to_summary(self):
        return {
            "request_id": self.ctx.request_id,
            "tenant_id": self.ctx.tenant_id,
            "agent_id": self.ctx.agent_id,
            "session_id": self.ctx.session_id,
            "llm_calls": self.llm_calls,
            "llm_input_tokens": self.llm_input_tokens,
            "llm_output_tokens": self.llm_output_tokens,
            "llm_cost": str(self.llm_cost),
            "tool_calls": self.tool_calls,
            "mcp_calls": self.mcp_calls,
            "retrieval_calls": self.retrieval_calls,
        }
```

---

## 13. 推荐目录映射

```text
platform/
  control_plane/
  gateway/
  runtime_ext/
    runtime_context.py
    runtime_dispatcher.py
    agent_factory.py
    agent_runtime_wrapper.py
    context_assembler.py
    session_manager.py
    request_usage_accumulator.py
  domain/
    models/
    repositories/
  capabilities/
    memory/
    knowledge/
    tools/
    mcp/
    models/
    workspace/
  bridge/
    config_mapper.py
    cowagent_runtime_adapter.py
    cowagent_tool_adapter.py
    cowagent_skill_adapter.py
    cowagent_model_adapter.py
```

---

## 14. 开发落地优先级

### 第一步
- RuntimeContext
- AgentDefinition
- SessionState
- Repository 接口

### 第二步
- Gateway
- Resolver
- AgentFactory
- AgentRuntimeWrapper

### 第三步
- UsageEventEmitter
- RequestUsageAccumulator
- Tool/MCP/Model 统一埋点

### 第四步
- Async job
- Worker
- Aggregation consumer

### 第五步
- Bridge layer 完整化
- Upstream compatibility tests
