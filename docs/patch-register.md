# Patch Register

本文档记录平台化过程中，对原有 CowAgent 上游文件做过的兼容修改。  
目标不是把所有变更都记在这里，而是把“未来升级时最容易冲突的 patch 点”明确下来。

## Patch 清单

### `agent/memory/conversation_store.py`

- 增加按 `workspace_root / db_path` 维度缓存 `ConversationStore`
- 平台模式下支持按 Agent 工作区隔离会话数据库
- 增加测试辅助的缓存重置函数

升级关注点：

- 如果上游调整会话存储实现，需要重新确认多 Agent 隔离是否仍然成立

### `bridge/agent_initializer.py`

- 平台模式下按当前运行时作用域切换工作区
- 合并 Agent 自定义 `system_prompt`
- 从 Agent 独立工作区恢复会话历史

升级关注点：

- 如果上游重构 Agent 初始化顺序，需要重新检查工作区解析和 prompt 合并逻辑

### `bridge/agent_bridge.py`

- 支持基于 `tenant_id + agent_id + session_id` 的实例缓存键
- 接入 runtime scope
- 接入 Phase 3 的 quota 校验和 usage 记录

升级关注点：

- 如果上游重构 `agent_reply()` 或消息持久化逻辑，需要重新验证 usage 与 quota 的接入点

### `channel/web/web_channel.py`

- 支持显式 `agent_id`
- 支持 `binding_id -> tenant_id + agent_id` 路由
- 支持 Agent 作用域下的 sessions/history/memory/knowledge API
- Web 内部轮询队列改为 scoped session key

升级关注点：

- 如果上游重构 web 控制台 API 或消息流处理，需要重新验证 binding 路由和 scoped queue

### `channel/web/chat.html`

- 新增 Agent 选择器
- 新增 binding 选择器

升级关注点：

- 如果上游大改前端结构，需要重新挂回平台选择控件

### `channel/web/static/js/console.js`

- 前端请求增加 `agent_id` / `binding_id` 透传
- 增加运行时作用域切换后的历史刷新、会话刷新逻辑

升级关注点：

- 如果上游重构前端状态管理，需要重新检查所有带作用域的 API 调用

### `pyproject.toml`

- 把 `cow_platform*` 纳入打包发现范围

升级关注点：

- 如果上游调整打包方式，需要确认 platform 模块仍会被安装

## 使用方式

吸收上游更新前：

1. 先阅读本文档，确认 patch 触点
2. 合并上游后，逐个检查这些文件是否有冲突或语义变化
3. 重新跑全量测试
4. 对 patch 清单做增删修订
