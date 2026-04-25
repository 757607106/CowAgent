# 渠道绑定、Agent 独立空间与记忆隔离设计说明

## 1. 文档目的

本文档用于明确 AI 中台在“渠道接入、Agent 路由、Agent 独立空间、长期记忆与梦境日记隔离”方面的设计原则与落地方式，避免后续研发过程中对以下概念产生混淆：

- 渠道与 Agent 的关系
- 默认 Agent 与自定义 Agent 的关系
- Agent Kernel 与 AgentDefinition 的关系
- 多渠道是否可以绑定同一个 Agent
- 每个 Agent 是否拥有独立空间
- 长期记忆、日级记忆、梦境蒸馏应如何在多个 Agent 间处理

---

## 2. 核心结论

### 2.1 渠道只是入口，不是业务实体

QQ、微信、网页、飞书、企微等都属于**消息入口渠道**。  
它们只负责接收消息并将消息路由到某个 Agent，不负责定义 Agent 的业务能力。

### 2.2 Agent 才是业务实体

售后客服、销售客服、默认办公助理、数据分析 Agent 等，都是**显性 AgentDefinition**，属于平台中的一等资源对象。

### 2.3 一个渠道可以绑定一个 Agent，多个渠道也可以绑定同一个 Agent

因此以下场景都应该支持：

- QQ → 售后客服 Agent
- 微信 → 销售客服 Agent

以及：

- QQ → 售后客服 Agent
- 微信 → 售后客服 Agent

### 2.4 每个 Agent 都必须拥有独立空间

这里的“独立空间”不能只理解成短期会话上下文，而应包含：

- 会话空间
- 长期记忆空间
- 梦境日记空间
- 工具权限空间
- MCP 权限空间
- 工作区 / 文件空间
- 缓存空间
- 审计空间
- 用量与成本空间

### 2.5 所有 Agent 应共享同一套记忆能力框架，但不共享记忆数据

也就是说：

- 默认 Agent 可以有核心记忆、日级记忆、梦境蒸馏
- 自定义 Agent 也应该支持这些能力
- 但每个 Agent 的记忆数据必须独立隔离，不能混用

---

## 3. 核心概念定义

## 3.1 Agent Kernel

Agent Kernel 指平台共享的一套通用 Agent 能力内核，负责：

- 上下文组装
- 记忆检索
- 知识检索
- 工具调度
- MCP 调用
- 模型调用
- 响应生成
- 规划与执行链

### 关键特征
- 通常全平台共享
- 不按租户复制一份
- 不按 Agent 单独复制一份
- 是平台底层运行引擎

## 3.2 AgentDefinition

AgentDefinition 是某个具体 Agent 的定义，是平台中的一等资源对象。

例如：

- default_assistant
- after_sales_agent
- sales_agent
- data_analyst_agent

### 一个 AgentDefinition 通常包含
- tenant_id
- agent_id
- name
- profile_type
- system_prompt
- model_config
- tool_policy
- mcp_policy
- skill_policy
- knowledge_bindings
- memory_policy
- quota_policy
- version
- status

## 3.3 AgentRuntime

AgentRuntime 是某个 AgentDefinition 在一次请求中的实际运行实例。

它是“运行时概念”，不是长期保存的资源对象。

## 3.4 ChannelBinding

ChannelBinding 描述某个渠道入口与某个 AgentDefinition 之间的绑定关系。

例如：

- QQ → after_sales_agent
- WeChat → sales_agent
- Web → default_assistant

## 3.5 Memory Engine

Memory Engine 是平台统一的记忆系统能力，包括：

- 核心记忆
- 日级记忆
- 梦境蒸馏
- 记忆检索
- 记忆压缩

所有 Agent 共享这套机制，但数据按 Agent 隔离。

---

## 4. 渠道与 Agent 的关系

## 4.1 正确建模方式

推荐建模如下：

```text
Tenant
 ├── AgentDefinitions
 │    ├── default_assistant
 │    ├── after_sales_agent
 │    ├── sales_agent
 │    └── data_analyst_agent
 │
 └── ChannelBindings
      ├── QQ      -> after_sales_agent
      ├── WeChat  -> sales_agent
      └── Web     -> default_assistant
```

### 解释
- 渠道只负责承接流量
- AgentDefinition 决定业务职责
- 渠道与 Agent 的关系应通过配置控制
- 不应该把业务能力硬编码在 channel 内

---

## 4.2 支持的一对一绑定

示例：

- QQ → 售后客服 Agent
- 微信 → 销售客服 Agent

这意味着：

### QQ 渠道进入
- 售后客服 prompt
- 售后知识库
- 售后工具
- 售后 MCP
- 售后记忆空间

### 微信渠道进入
- 销售 prompt
- 销售知识库
- 销售工具
- 销售 MCP
- 销售记忆空间

---

## 4.3 支持的多渠道绑定同一 Agent

示例：

- QQ → 售后客服 Agent
- 微信 → 售后客服 Agent
- 网页客服入口 → 售后客服 Agent

这意味着：

### 三个渠道共享
- 同一 AgentDefinition
- 同一套 prompt
- 同一套工具权限
- 同一套知识绑定
- 同一套长期记忆策略
- 同一套成本归因目标 Agent

### 但不意味着
- 自动共享同一个 session
- 自动把不同渠道的短期上下文混成一个会话

---

## 5. 每个 Agent 的独立空间设计

## 5.1 总原则

系统必须保证：

**每个 AgentDefinition 都有自己的独立命名空间。**

即使多个 Agent 共用同一套内核，也不能共用运行数据空间。

---

## 5.2 会话空间

### 作用
用于存放：

- 会话历史
- 当前轮次状态
- 工具调用轨迹
- 中间摘要
- 临时执行状态

### 建议命名空间

```text
tenant:{tenant_id}:agent:{agent_id}:session:{session_id}
```

### 设计要求
- 不同 Agent 的 session 绝不能混用
- 同一 Agent 下不同 session 也要隔离
- 不同渠道进入同一 Agent，也不应默认共用 session

---

## 5.3 长期记忆空间

### 作用
用于存放：

- 核心记忆
- 历史偏好
- 用户长期画像
- 工作习惯
- 长期对话提炼结果

### 建议命名空间

```text
tenant:{tenant_id}:agent:{agent_id}:memory
```

### 设计要求
- 每个 Agent 独立
- 售后客服 Agent 的长期记忆不能进入销售客服 Agent
- 默认 Agent 也有自己的独立长期记忆空间

---

## 5.4 日级记忆空间

### 作用
用于存放：
- 当日日志
- 当日总结
- 日级摘要

### 建议命名空间

```text
tenant:{tenant_id}:agent:{agent_id}:daily_memory:{date}
```

### 设计要求
- 每个 Agent 每天独立累计
- 不允许跨 Agent 混合汇总

---

## 5.5 梦境蒸馏空间

### 作用
用于存放：
- 梦境蒸馏结果
- 长周期压缩记忆
- 从日级记忆中抽取出的更高层知识

### 建议命名空间

```text
tenant:{tenant_id}:agent:{agent_id}:dream_memory
```

### 设计要求
- 每个 Agent 独立生成自己的梦境
- 售后客服 Agent 的梦境来自售后历史
- 销售客服 Agent 的梦境来自销售历史
- 数据分析 Agent 的梦境来自分析任务历史

---

## 5.6 知识访问空间

知识空间不一定要求物理独占，但**访问权限必须按 Agent 独立控制**。

### 例子
- after_sales_agent 绑定售后知识库
- sales_agent 绑定产品销售知识库
- data_analyst_agent 绑定数据字典与报表规范

### 设计原则
- 一个知识空间可以被多个 Agent 绑定
- 但每个 Agent 只能访问自己被允许访问的知识空间
- 运行时必须通过 Agent 的 binding 做过滤

---

## 5.7 工具空间

### 作用
定义某个 Agent 能调用哪些工具。

### 例子

#### 售后客服 Agent
可用：
- FAQ 查询
- 工单查询
- CRM 查询

禁用：
- Python
- Shell
- Browser

#### 销售客服 Agent
可用：
- 客户资料查询
- 产品报价
- 订单状态查询

#### 数据分析 Agent
可用：
- Python
- SQL
- 文件处理

### 设计要求
- 工具引擎可以共享
- 工具权限必须按 Agent 白名单控制

---

## 5.8 MCP 空间

MCP 调用边界也必须按 Agent 独立控制。

### 例子
- 售后客服 Agent 只能访问售后相关 MCP
- 销售客服 Agent 只能访问销售相关 MCP
- 数据分析 Agent 只能访问数据分析相关 MCP

### 设计要求
- MCP client 可共享
- MCP server / method 白名单必须按 Agent 生效

---

## 5.9 文件与工作区空间

### 作用
用于存放：
- 上传文件
- 临时处理文件
- 分析产物
- 导出内容
- 工具执行产物

### 建议路径

```text
/workspaces/{tenant_id}/{agent_id}/
/tmp/{tenant_id}/{agent_id}/{session_id}/
/artifacts/{tenant_id}/{agent_id}/
```

### 设计要求
- 不同 Agent 文件严格隔离
- 不允许售后客服 Agent 读到销售客服 Agent 文件
- 不允许默认 Agent 看到数据分析 Agent 的分析产物

---

## 5.10 缓存空间

建议缓存也按 Agent 维度隔离：

```text
cache:{tenant_id}:{agent_id}:...
```

### 适用场景
- retrieval cache
- agent runtime cache
- request summary cache

---

## 5.11 审计空间

审计与日志至少要能按 Agent 检索：

- 调用了哪个工具
- 调了哪个 MCP
- 访问了哪些知识空间
- 生成了哪些 artifact

### 建议维度
- tenant_id
- agent_id
- session_id
- request_id
- channel_type

---

## 5.12 Usage 与成本空间

所有 token、tool、MCP、retrieval、artifact 的用量和成本，都必须归因到具体 Agent。

### 必须归因的字段
- tenant_id
- agent_id
- user_id
- session_id
- request_id
- channel_type

---

## 6. 记忆系统设计：能力一致，数据隔离

## 6.1 正确原则

所有 Agent 应该共享同一套 Memory Engine，但每个 Agent 独立保存自己的记忆数据。

### 也就是说
- 机制一致
- 数据不共享

---

## 6.2 统一能力框架

所有 Agent 应可支持：

- 核心记忆
- 日级记忆
- 梦境蒸馏
- 关键词检索
- 向量检索
- 记忆压缩
- 会话摘要

---

## 6.3 独立记忆数据

### 错误做法
- 所有 Agent 共用一份记忆池

### 正确做法
- 每个 Agent 有自己的 memory namespace
- 每个 Agent 有自己的 daily memory
- 每个 Agent 有自己的 dream memory

---

## 6.4 为什么必须独立

原因包括：

1. 职责不同  
   售后客服和销售客服关注的信息完全不同。

2. 话术不同  
   不同 Agent 的长期风格不应相互污染。

3. 风险隔离  
   数据分析 Agent 处理的数据不应进入客服 Agent 记忆。

4. 统计清晰  
   成本、效果、行为分析都要按 Agent 分开看。

---

## 7. 默认 Agent 与自定义 Agent 的关系

## 7.1 默认 Agent 的定位

建议每个租户都可以拥有一个系统预置的默认通用 Agent，例如：

- `default_assistant`

### 特点
- 由系统创建
- 作为租户默认入口
- 与用户创建的 Agent 同属 AgentDefinition

## 7.2 自定义 Agent 的定位

例如：

- `after_sales_agent`
- `sales_agent`
- `data_analyst_agent`

### 特点
- 由租户管理员创建
- 明确业务职责
- 与默认 Agent 共享同一套内核
- 但拥有独立空间和独立配置

## 7.3 关键结论

默认 Agent 不是特殊例外。  
它应与自定义 Agent 遵循同样的规则：

- 同样有独立空间
- 同样有独立记忆
- 同样有独立 usage 统计
- 同样可绑定渠道

---

## 8. 多渠道接入下的 Session 设计

## 8.1 不建议默认跨渠道共享 Session

例如：

- 同一个客户在 QQ 联系
- 又在微信联系
- 两边都绑定到同一个售后客服 Agent

### 建议默认行为
- 同一 AgentDefinition
- 不同渠道仍创建不同 session

原因：
- 更安全
- 更可控
- 更容易排障
- 避免不同渠道短期上下文混乱

---

## 8.2 跨渠道共享长期记忆可以做，但要谨慎

如果后续你做了租户内用户身份映射，例如：

- QQ 用户 A
- 微信用户 A
- 都映射到同一个 tenant_user

那么可以考虑：

- 长期记忆层引用同一用户画像
- 但短期会话仍分 session

### 第一阶段建议
默认不做复杂跨渠道短期上下文合并。

---

## 9. 推荐建模方式

## 9.1 AgentDefinition 增加字段

建议至少包含：

- `is_system_default`
- `created_source`

例如：

- `is_system_default = true/false`
- `created_source = system/user/template/import`

## 9.2 ChannelBinding 建模

```text
binding_id
tenant_id
channel_type
external_app_id
external_chat_id
external_user_id
agent_id
route_mode
```

---

## 10. 典型场景示例

## 10.1 场景 A：不同渠道绑定不同 Agent

```text
QQ      -> after_sales_agent
WeChat  -> sales_agent
Web     -> default_assistant
```

### 效果
- QQ 消息进入售后空间
- 微信消息进入销售空间
- Web 消息进入默认助理空间

三者完全隔离。

---

## 10.2 场景 B：多个渠道绑定同一个 Agent

```text
QQ      -> after_sales_agent
WeChat  -> after_sales_agent
Web     -> after_sales_agent
```

### 效果
- 三个渠道共享同一个 AgentDefinition
- 共享同一套长期记忆空间
- 共享同一套工具权限
- 共享同一套知识绑定
- 但默认不共享同一个短期 session

---

## 10.3 场景 C：租户同时有多个 Agent

```text
Tenant A
 ├── default_assistant
 ├── after_sales_agent
 ├── sales_agent
 └── data_analyst_agent
```

### 渠道路由示例
- QQ → after_sales_agent
- 微信 → sales_agent
- Web 控制台 → default_assistant
- 内部数据门户 → data_analyst_agent

---

## 11. 用量与成本归因要求

无论消息来自哪个渠道，只要最终进入某个 AgentRuntime，消耗都必须归因到对应 Agent。

## 11.1 必须归因的维度

- tenant_id
- agent_id
- channel_type
- user_id
- session_id
- request_id

## 11.2 必须统计的内容

### LLM
- input_tokens
- output_tokens
- model_name
- provider
- 成本

### Tool
- tool_name
- 调用次数
- 成功/失败
- 耗时

### MCP
- mcp_server_name
- method
- 调用次数
- 成功/失败
- 耗时

### Artifact / Retrieval
- 文件读写次数
- 检索次数
- 生成物数量

---

## 12. 落地规则建议

建议直接把以下规则写进架构规范：

### 规则 1
平台只有一套共享 Agent Kernel。

### 规则 2
每个租户下可以有多个显性 AgentDefinition。

### 规则 3
每个 AgentDefinition 必须拥有独立命名空间。

### 规则 4
所有 Agent 共享同一套 Memory Engine 能力，但记忆数据按 Agent 隔离。

### 规则 5
渠道只负责将消息路由到 Agent，不允许在渠道层定义业务能力。

### 规则 6
同一个 Agent 可以绑定多个渠道。

### 规则 7
不同渠道默认不共享同一个 session。

### 规则 8
所有运行消耗都必须归因到具体 Agent。

---

## 13. 最终结论

本项目中，“每个 Agent 都有独立空间”应作为硬约束执行。

这里的独立空间包括：

- 会话空间
- 长期记忆空间
- 日级记忆空间
- 梦境蒸馏空间
- 工具权限空间
- MCP 权限空间
- 文件与工作区空间
- 缓存空间
- 审计空间
- 用量与成本空间

同时，渠道与 Agent 的关系应理解为：

- 渠道是入口
- Agent 是业务实体
- 渠道通过绑定关系路由到某个 Agent
- 一个渠道可以对应一个 Agent
- 多个渠道也可以对应同一个 Agent

最终应形成的结构不是“渠道驱动能力”，而是“渠道驱动路由，Agent 驱动业务能力”。

---

## 14. 建议的后续文档

建议在本文档基础上，继续补充：

1. 《ChannelBinding 表结构与路由规则设计》
2. 《Memory Engine 与梦境蒸馏数据结构设计》
3. 《Agent Namespace 与 Workspace 规范》
4. 《多渠道用户身份映射设计》
5. 《Usage Metering 与 Agent 归因说明》
