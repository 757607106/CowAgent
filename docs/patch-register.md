# Patch Register

本文档记录平台化过程中，对原有 CowAgent 上游文件做过的兼容修改。  
目标不是把所有变更都记在这里，而是把“未来升级时最容易冲突的 patch 点”明确下来。

当前二开基线把上游 CowAgent 作为 Agent 内核，平台能力优先落在 `cow_platform/`。
上游参考版本：<https://github.com/zhayujie/CowAgent/tree/2.0.7>

## Patch 清单

### `app.py`

- 多租户鉴权开启时，启动阶段只保留 `web` 控制台，不再根据 `config.json/channel_type` 启动微信、飞书、QQ 等全局渠道
- 启动后仍会从租户数据库加载已启用的渠道配置，并按 `channel_config_id` 维度启动托管运行时

升级关注点：

- 如果上游调整应用启动或 ChannelManager，需要重新确认租户渠道仍只来自数据库配置

### `config.py`

- `Config.get()` / `Config.__getitem__()` 会优先读取当前 runtime scope 中的配置覆盖
- 平台托管渠道运行时通过该覆盖机制注入模型、渠道密钥等租户级配置

升级关注点：

- 如果上游调整全局配置读取方式，需要重新确认 runtime scope 覆盖仍先于根 `config.json`

### `agent/memory/conversation_store.py`

- 增加按 `workspace_root / db_path` 维度缓存 `ConversationStore`
- 平台模式下支持按 Agent 工作区隔离会话数据库
- 增加测试辅助的缓存重置函数

升级关注点：

- 如果上游调整会话存储实现，需要重新确认多 Agent 隔离是否仍然成立

### `agent/memory/storage.py`

- 长期记忆存储使用平台 Agent 工作区路径派生隔离命名空间

升级关注点：

- 如果上游重构长期记忆索引路径，需要重新确认租户/Agent 工作区不会串用

### `agent/protocol/agent_stream.py`

- 思考输出开关会读取当前平台 runtime context

升级关注点：

- 如果上游调整流式输出或 thinking 控制，需要重新检查平台 Agent 策略是否仍能生效

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

### `channel/web/frontend_layout.py`

- Web 前端入口路径集中在该文件解析
- modern 前端固定使用 `channel/web/frontend/modern/dist`
- legacy 静态前端保留在 `channel/web/frontend/legacy` 作为历史 patch 参考

升级关注点：

- 如果上游调整 Web 静态资源目录或路由，需要先复核这里的前端路径解析

### `channel/channel.py`

- Channel 基类增加 `channel_config_id`、`tenant_id`、`config_overrides`
- 托管渠道实例通过这些字段携带租户运行时配置

升级关注点：

- 如果上游调整 Channel 生命周期或字段初始化，需要重新确认托管渠道仍能注入平台上下文

### `channel/chat_channel.py`

- ChatChannel 支持按 `binding_id` 或渠道身份解析目标 Agent
- 消息 context 会注入 `binding_id`、`tenant_id`、`agent_id`、租户用户身份和 config overrides

升级关注点：

- 如果上游调整终端/聊天通道消息上下文，需要重新验证 binding 解析和身份映射

### `channel/qq/qq_channel.py`

- 平台托管运行时会向消息 context 注入 `channel_config_id` 与 `source_tenant_id`

升级关注点：

- 如果上游调整 QQ 消息构造流程，需要重新挂回租户渠道上下文

### `channel/weixin/weixin_channel.py`

- 平台托管运行时会向消息 context 注入 `channel_config_id` 与 `source_tenant_id`

升级关注点：

- 如果上游调整微信消息构造流程，需要重新挂回租户渠道上下文

### `channel/wecom_bot/wecom_bot_channel.py`

- 平台托管运行时会向消息 context 注入 `channel_config_id` 与 `source_tenant_id`

升级关注点：

- 如果上游调整企微机器人消息构造流程，需要重新挂回租户渠道上下文

### `channel/feishu/feishu_channel.py`

- 平台托管运行时会向消息 context 注入 `channel_config_id` 与 `source_tenant_id`

升级关注点：

- 如果上游调整飞书消息构造流程，需要重新挂回租户渠道上下文

### `channel/web/frontend/legacy/chat.html`

- 新增 Agent 选择器
- 新增 binding 选择器
- 该文件仅作为旧版静态前端的历史 patch 参考，运行时默认使用 modern 前端

升级关注点：

- 如果上游大改前端结构，需要重新挂回平台选择控件

### `channel/web/frontend/legacy/static/js/console.js`

- 前端请求增加 `agent_id` / `binding_id` 透传
- 增加运行时作用域切换后的历史刷新、会话刷新逻辑
- 该文件仅作为旧版静态前端的历史 patch 参考，运行时默认使用 modern 前端

升级关注点：

- 如果上游重构前端状态管理，需要重新检查所有带作用域的 API 调用

### `channel/web/frontend/modern/`

- 平台 Web 控制台的 React + TypeScript + Vite 前端源码
- `/chat` 由 `channel/web/frontend_layout.py` 固定渲染 `frontend/modern/dist/index.html`
- `/assets/*` 仅从 `frontend/modern/dist/` 解析构建产物

升级关注点：

- 如果上游调整 Web 控制台入口，需要重新确认 modern 前端构建目录和 `/assets/*` 路由仍一致

### `pyproject.toml`

- 把 `cow_platform*` 纳入打包发现范围

升级关注点：

- 如果上游调整打包方式，需要确认 platform 模块仍会被安装

### `cli/commands/platform.py`

- 新增 `cow platform` 治理、doctor、worker 相关命令

升级关注点：

- 如果上游调整 CLI 命令加载方式，需要确认 platform 命令仍能注册

### `docker/entrypoint.sh`

- 支持平台 API / worker 等部署入口

升级关注点：

- 如果上游调整容器启动脚本，需要重新确认 legacy 与 platform 两种模式都能启动

### `docker/compose.platform.yml`

- 定义平台 API、worker、PostgreSQL 等运行组件

升级关注点：

- 如果上游调整 compose 文件组织方式，需要重新确认平台部署文件不被覆盖

## 使用方式

吸收上游更新前：

1. 先阅读本文档，确认 patch 触点
2. 合并上游后，逐个检查这些文件是否有冲突或语义变化
3. 重新跑全量测试
4. 对 patch 清单做增删修订
