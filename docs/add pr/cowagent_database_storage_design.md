# 数据库与存储设计文档

## 1. 目标

本文档针对基于 CowAgent 二次开发的 AI 中台，给出数据库、缓存、向量库、对象存储、消息流与主要表结构设计，目标是：

- 支持单实例多租户
- 支持显性 Agent
- 保证租户与 Agent 隔离
- 支持 usage metering 与成本统计
- 支持 Docker 一键部署
- 保证开发、测试、生产环境依赖一致

---

## 2. 数据存储总体选型

## 2.1 PostgreSQL

用途：

- Tenant / User / AgentDefinition 元数据
- Binding / Policy / Quota
- Session 元数据
- Job 元数据
- Usage 聚合结果
- Pricing Catalog
- Audit 索引

## 2.2 Redis

用途：

- Session 热状态
- Rate limit
- Quota counter
- Runtime cache
- Retrieval cache
- Request 级短期汇总
- Redis Streams 事件流

## 2.3 Qdrant

用途：

- Knowledge 向量
- Long-term Memory 向量
- Embedding 索引

## 2.4 MinIO

用途：

- 上传文件
- Artifact
- 分析产物
- 导出文件
- 大对象结果

---

## 3. 命名空间设计

统一使用：

```text
tenant_ns  = tenant:{tenant_id}
agent_ns   = tenant:{tenant_id}:agent:{agent_id}
session_ns = tenant:{tenant_id}:agent:{agent_id}:session:{session_id}
user_ns    = tenant:{tenant_id}:user:{user_id}
```

---

## 4. PostgreSQL 表设计

## 4.1 tenants

```sql
create table tenants (
  tenant_id        varchar(64) primary key,
  name             varchar(255) not null,
  status           varchar(32) not null,
  created_at       timestamp not null,
  updated_at       timestamp not null
);
```

## 4.2 tenant_users

```sql
create table tenant_users (
  tenant_id        varchar(64) not null,
  user_id          varchar(64) not null,
  name             varchar(255),
  role             varchar(64) not null,
  status           varchar(32) not null,
  created_at       timestamp not null,
  updated_at       timestamp not null,
  primary key (tenant_id, user_id)
);
```

## 4.3 tenant_user_identities

用于将同一个租户用户映射到多个渠道身份。

```sql
create table tenant_user_identities (
  tenant_id        varchar(64) not null,
  user_id          varchar(64) not null,
  channel_type     varchar(64) not null,
  external_user_id varchar(255) not null,
  created_at       timestamp not null,
  primary key (tenant_id, channel_type, external_user_id)
);
```

## 4.4 agent_definitions

```sql
create table agent_definitions (
  tenant_id             varchar(64) not null,
  agent_id              varchar(64) not null,
  name                  varchar(255) not null,
  profile_type          varchar(64) not null,
  description           text,
  system_prompt         text not null,
  model_config_json     jsonb not null,
  context_policy_json   jsonb not null,
  memory_policy_json    jsonb not null,
  tool_policy_json      jsonb not null,
  skill_policy_json     jsonb not null,
  quota_policy_json     jsonb not null,
  status                varchar(32) not null,
  version               integer not null,
  created_at            timestamp not null,
  updated_at            timestamp not null,
  primary key (tenant_id, agent_id)
);
```

建议索引：

```sql
create index idx_agent_definitions_tenant_status
on agent_definitions (tenant_id, status);
```

## 4.5 agent_definition_versions

用于回滚与灰度。

```sql
create table agent_definition_versions (
  tenant_id             varchar(64) not null,
  agent_id              varchar(64) not null,
  version               integer not null,
  snapshot_json         jsonb not null,
  created_at            timestamp not null,
  created_by            varchar(64),
  primary key (tenant_id, agent_id, version)
);
```

## 4.6 channel_bindings

```sql
create table channel_bindings (
  binding_id            varchar(64) primary key,
  tenant_id             varchar(64) not null,
  agent_id              varchar(64) not null,
  channel_type          varchar(64) not null,
  external_app_id       varchar(255),
  external_chat_id      varchar(255),
  external_user_id      varchar(255),
  route_mode            varchar(64) not null,
  created_at            timestamp not null,
  updated_at            timestamp not null
);
```

## 4.7 knowledge_spaces

```sql
create table knowledge_spaces (
  tenant_id             varchar(64) not null,
  space_id              varchar(64) not null,
  name                  varchar(255) not null,
  storage_type          varchar(64) not null,
  config_json           jsonb not null,
  status                varchar(32) not null,
  created_at            timestamp not null,
  updated_at            timestamp not null,
  primary key (tenant_id, space_id)
);
```

## 4.8 agent_knowledge_bindings

```sql
create table agent_knowledge_bindings (
  tenant_id             varchar(64) not null,
  agent_id              varchar(64) not null,
  space_id              varchar(64) not null,
  created_at            timestamp not null,
  primary key (tenant_id, agent_id, space_id)
);
```

## 4.9 sessions

```sql
create table sessions (
  tenant_id             varchar(64) not null,
  agent_id              varchar(64) not null,
  session_id            varchar(64) not null,
  user_id               varchar(64) not null,
  channel_type          varchar(64) not null,
  status                varchar(32) not null,
  created_at            timestamp not null,
  updated_at            timestamp not null,
  primary key (tenant_id, agent_id, session_id)
);
```

## 4.10 jobs

```sql
create table jobs (
  tenant_id             varchar(64) not null,
  agent_id              varchar(64) not null,
  job_id                varchar(64) not null,
  session_id            varchar(64),
  user_id               varchar(64),
  job_type              varchar(64) not null,
  status                varchar(32) not null,
  payload_json          jsonb not null,
  result_json           jsonb,
  created_at            timestamp not null,
  updated_at            timestamp not null,
  primary key (tenant_id, agent_id, job_id)
);
```

## 4.11 pricing_catalog

```sql
create table pricing_catalog (
  pricing_id            varchar(64) primary key,
  provider              varchar(64) not null,
  resource_type         varchar(64) not null,
  resource_name         varchar(255) not null,
  billing_unit          varchar(64) not null,
  price_per_unit        numeric(18, 8) not null,
  currency              varchar(16) not null,
  effective_from        timestamp not null,
  effective_to          timestamp,
  status                varchar(32) not null,
  metadata_json         jsonb
);
```

## 4.12 usage_ledger

append-only 明细账本。

```sql
create table usage_ledger (
  event_id              varchar(64) primary key,
  event_type            varchar(64) not null,
  event_time            timestamp not null,

  tenant_id             varchar(64) not null,
  agent_id              varchar(64) not null,
  user_id               varchar(64),
  session_id            varchar(64),
  request_id            varchar(64),
  job_id                varchar(64),

  provider              varchar(128),
  resource_name         varchar(255),
  status                varchar(32) not null,

  input_units           bigint,
  output_units          bigint,
  latency_ms            integer,

  raw_cost              numeric(18, 6),
  currency              varchar(16),

  metadata_json         jsonb not null default '{}'::jsonb
);
```

建议索引：

```sql
create index idx_usage_ledger_tenant_time on usage_ledger (tenant_id, event_time);
create index idx_usage_ledger_agent_time on usage_ledger (tenant_id, agent_id, event_time);
create index idx_usage_ledger_request on usage_ledger (request_id);
```

## 4.13 tenant_daily_usage

```sql
create table tenant_daily_usage (
  usage_date            date not null,
  tenant_id             varchar(64) not null,

  llm_call_count        bigint not null default 0,
  llm_input_tokens      bigint not null default 0,
  llm_output_tokens     bigint not null default 0,
  llm_cost              numeric(18, 6) not null default 0,

  tool_call_count       bigint not null default 0,
  tool_success_count    bigint not null default 0,
  tool_failure_count    bigint not null default 0,

  mcp_call_count        bigint not null default 0,
  mcp_success_count     bigint not null default 0,
  mcp_failure_count     bigint not null default 0,

  retrieval_count       bigint not null default 0,
  embedding_tokens      bigint not null default 0,

  total_cost            numeric(18, 6) not null default 0,
  updated_at            timestamp not null,

  primary key (usage_date, tenant_id)
);
```

## 4.14 agent_daily_usage

```sql
create table agent_daily_usage (
  usage_date            date not null,
  tenant_id             varchar(64) not null,
  agent_id              varchar(64) not null,

  llm_call_count        bigint not null default 0,
  llm_input_tokens      bigint not null default 0,
  llm_output_tokens     bigint not null default 0,
  llm_cost              numeric(18, 6) not null default 0,

  tool_call_count       bigint not null default 0,
  mcp_call_count        bigint not null default 0,
  total_cost            numeric(18, 6) not null default 0,

  updated_at            timestamp not null,
  primary key (usage_date, tenant_id, agent_id)
);
```

## 4.15 审计索引表

```sql
create table audit_logs (
  audit_id              varchar(64) primary key,
  event_time            timestamp not null,
  tenant_id             varchar(64) not null,
  agent_id              varchar(64),
  user_id               varchar(64),
  session_id            varchar(64),
  request_id            varchar(64),
  action_type           varchar(64) not null,
  status                varchar(32) not null,
  summary               text,
  metadata_json         jsonb not null default '{}'::jsonb
);
```

---

## 5. Redis 设计

## 5.1 Key 规范

```text
sess:{tenant_id}:{agent_id}:{session_id}:history
sess:{tenant_id}:{agent_id}:{session_id}:state
quota:{tenant_id}
quota:{tenant_id}:{agent_id}
rate:{tenant_id}:{user_id}
cache:agent_runtime:{tenant_id}:{agent_id}:{version}
cache:retrieval:{tenant_id}:{agent_id}:{query_hash}
usage:req:{request_id}:summary
stream:usage_events
stream:jobs
```

## 5.2 用途

- Session 热上下文
- 限流
- Quota 计数器
- Runtime cache
- Retrieval cache
- 短时 request usage 汇总
- Redis Streams 事件流

---

## 6. Qdrant 设计

## 6.1 Collection 命名方案

### 方案 A：按 tenant/agent 分集合

```text
mem__tenant_{tenant_id}__agent_{agent_id}
kb__tenant_{tenant_id}__space_{space_id}
```

### 方案 B：单集合 + payload filter

适合规模更大但实现复杂度略高。

### 第一阶段建议

优先用方案 A，简单直接，隔离边界清晰。

## 6.2 Payload 字段

- tenant_id
- agent_id
- space_id
- doc_id
- chunk_id
- source_type
- created_at
- tags

---

## 7. MinIO 设计

## 7.1 Bucket 建议

- `uploads`
- `artifacts`
- `exports`
- `archives`

## 7.2 对象路径规范

```text
uploads/{tenant_id}/{agent_id}/{date}/{file_id}
artifacts/{tenant_id}/{agent_id}/{session_id}/{artifact_id}
exports/{tenant_id}/{agent_id}/{job_id}/{file_name}
```

---

## 8. 数据保留策略

## 8.1 Usage Ledger

建议按时间分区，保留长期审计能力。

## 8.2 Session 热状态

Redis 中设置 TTL，长期内容归档到 PG / MinIO。

## 8.3 Artifact

按租户策略保留，支持生命周期管理。

---

## 9. Migration 规范

- 所有环境统一用同一套 migration
- 禁止手工修改生产 schema
- migration 必须可回滚
- CI 中必须执行 migration 验证

---

## 10. 第一阶段与第二阶段扩展

## 第一阶段

- PG + Redis + Qdrant + MinIO
- 使用 Redis Streams 做 usage/job 事件流

## 第二阶段

- 大规模 usage analytics 时引入 ClickHouse
- 更高吞吐异步需求时评估 Kafka / RabbitMQ
