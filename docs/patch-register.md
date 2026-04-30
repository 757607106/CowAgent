# Patch Register

本文档记录平台化过程中，对原有 CowAgent 上游文件做过的兼容修改。  
目标不是把所有变更都记在这里，而是把“未来升级时最容易冲突的 patch 点”明确下来。

当前二开基线把上游 CowAgent 作为 Agent 内核，平台能力优先落在 `cow_platform/`。
上游参考版本：<https://github.com/zhayujie/CowAgent/tree/2.0.7>

## Patch 清单

### `app.py`

- 平台模式启动入口只负责加载配置、启动 Web 控制台和注册信号处理
- `ChannelManager` 已抽离到 `cow_platform/runtime/channel_manager.py`，`app.py` 仅保留兼容导出

升级关注点：

- 如果上游调整应用启动，需要确认 Web 进程不会重新默认承载长连接/轮询渠道
- 如果上游调整 ChannelManager，需要合并到平台 runtime 层，不要重新塞回 `app.py`

### `config.py`

- `Config.get()` / `Config.__getitem__()` 会优先读取当前 runtime scope 中的配置覆盖
- 平台托管渠道运行时通过该覆盖机制注入模型、渠道密钥等租户级配置
- 平台模式不读取项目根目录 `config.json` / `config-template.json`，启动层来自环境变量，平台运行时配置来自 PostgreSQL `platform_settings`
- 数据库平台设置会覆盖内存配置，并同步到环境变量供子进程使用，避免旧环境变量压过平台数据库配置
- 平台租户模式不再读取或保存全局 `user_datas.pkl`，运行期 `get_user_data()` 也返回 no-op 视图，避免不同租户的外部用户 ID 复用 legacy 用户级模型/API key
- `platform_start_channel_runtimes` 默认关闭，用于把 Web 进程与租户渠道 runtime worker 解耦

升级关注点：

- 如果上游调整全局配置读取方式，需要重新确认优先级仍是 runtime scope > platform_settings > environment > 内置默认值
- 如果上游重新引入用户级 legacy 配置持久化，需要确认平台模式不会落回全局 pickle 文件或全局内存字典

### `cow_platform/db/postgres.py`

- 平台 PostgreSQL 访问增加连接池，减少高频仓储调用反复建连的开销
- 增加版本化 migration runner 和 `platform_schema_migrations` 迁移登记表，容器启动、CLI 与测试共用同一套 schema 入口
- 增加 `platform_scheduled_tasks` 表，作为定时任务在平台模式下的唯一配置真源
- 增加 `platform_channel_runtime_leases` 表，作为托管渠道运行时的分布式所有权记录
- 增加 `platform_runtime_state` 表，作为 runtime desired state、config_version 和 invalidation 的统一真源
- 增加 `platform_skill_configs` 表，作为平台模式下 skills_config 的租户/Agent 级配置真源
- `platform_memory_chunks` 在 pgvector 可用时增加 `embedding_vector` 和 HNSW 索引；pgvector 不可用时保留 JSONB embedding 回退

升级关注点：

- 如果上游调整数据库初始化方式，需要确认平台连接池、版本化 migration、调度任务表、runtime state、技能配置、渠道运行时 lease 表和 memory vector schema 仍会初始化

### `cow_platform/runtime/channel_manager.py`

- 平台 ChannelManager 的唯一实现位置，负责本地 Web channel、租户托管渠道、lease、heartbeat、singleton cache 清理和运行时配置覆盖
- `app.py` 与 `cow_platform/worker/channel_runtime.py` 都引用该模块，避免 Web 入口和 runtime worker 各自维护一套渠道生命周期逻辑

升级关注点：

- 如果上游调整渠道生命周期，需要确认托管渠道仍按 `channel_config_id` 获取 lease 后才能启动
- 如果上游新增渠道 singleton 或启动约束，需要在这里统一维护，不要分散到 `app.py` 或 Web handler

### `cow_platform/db/migrate.py`

- 容器启动 migration 入口改为调用版本化 `run_migrations()`，输出实际应用的 migration 版本

升级关注点：

- 如果上游调整容器入口或数据库初始化脚本，需要确认仍调用同一套版本化 migration runner

### `cow_platform/services/channel_runtime_service.py`

- 新增托管渠道运行时 lease 服务，按 `channel_config_id` 原子获取、续租和释放运行时所有权
- 只有当前实例 owner 可以续租或释放，lease 过期后其他实例才能接管

升级关注点：

- 如果上游调整托管渠道启动方式，需要保留 acquire/heartbeat/release 生命周期，避免多实例重复拉起同一渠道

### `cow_platform/worker/channel_runtime.py`

- 新增租户渠道 runtime worker，按数据库已启用渠道配置定期 sync 启停后台 runtime
- Web 进程只负责 Web/API；飞书 websocket、QQ、钉钉、企微等长连接/轮询渠道由该 worker 持有

升级关注点：

- 如果上游调整 worker 或部署入口，需要确认 `cow platform channel-runtime` 与容器服务仍能独立启动租户渠道 runtime

### `cow_platform/services/scheduler_task_store.py`

- 新增 DB-backed scheduler task store，所有任务按 `tenant_id + agent_id + task_id` 隔离
- 工具/UI 使用 scoped store，只能读写当前租户和 Agent 的任务；后台调度使用 unscoped store 扫描到期任务

升级关注点：

- 如果上游调整 scheduler 存储接口，需要保留 tenant/agent scope，不能重新把任务写回全局 `tasks.json`

### `cow_platform/services/platform_config_service.py`

- `platform_settings` 表承载平台级运行时配置，替代 Web 控制台写 `config.json`
- 该服务只保存平台级设置；租户渠道、模型、Agent、MCP、技能等仍使用各自租户隔离表
- 平台设置更新后 bump platform runtime config_version，使跨进程 Agent cache 在下一次请求时失效

升级关注点：

- 如果上游新增平台级配置入口，需要接入该服务，不能重新写回根 `config.json`

### `cow_platform/services/runtime_state_service.py`

- 统一维护 platform / tenant / agent / channel_config scope 的 runtime state 与 config_version
- Agent 运行时有效版本由 platform、tenant、agent 三层版本合并得到，跨进程通过 PostgreSQL 版本变化触发本进程缓存失效
- 所有配置写入口应调用该服务 bump version，避免直接操作 AgentBridge 进程内缓存

升级关注点：

- 如果上游新增会影响运行时的配置资源，必须接入该服务的 invalidation，不要增加新的本地缓存清理路径

### `cow_platform/services/skill_config_service.py`

- 平台模式下 `skills_config` 迁入 `platform_skill_configs`
- 配置按 `tenant_id + agent_id + skill_name` 隔离，更新时 bump 对应 Agent 的 config_version

升级关注点：

- 如果上游调整 SkillManager 的配置读写，需要确认平台模式仍不写 workspace `skills_config.json`

### `agent/memory/conversation_store.py`

- 增加按 `workspace_root / db_path` 维度缓存 `ConversationStore`
- 平台模式下支持按 Agent 工作区隔离会话数据库
- 增加测试辅助的缓存重置函数

升级关注点：

- 如果上游调整会话存储实现，需要重新确认多 Agent 隔离是否仍然成立

### `agent/memory/storage.py`

- 长期记忆存储使用平台 Agent 工作区路径派生隔离命名空间
- embedding 写入优先同步到 PostgreSQL `vector` 列，向量搜索优先走 pgvector 距离排序
- 当 pgvector 扩展、列或索引不可用时保留 JSONB embedding + Python cosine 回退，避免部署环境缺扩展导致 memory 功能不可用

升级关注点：

- 如果上游重构长期记忆索引路径，需要重新确认租户/Agent 工作区不会串用，且向量搜索不会退回全表 JSON 扫描作为唯一生产路径

### `agent/tools/*`

- 文件类工具统一限制在当前 Agent 工作区内访问，绝对路径、`~` 路径或 `..` 越界路径不能读取/写入其他租户工作区
- `bash` 工具运行目录仍是当前 Agent 工作区，并在执行前拦截明显的跨工作区路径访问；大输出临时文件也保存到当前工作区 `tmp/`

升级关注点：

- 如果上游调整 `read/write/edit/ls/send/bash` 或新增文件访问类工具，需要重新接入工作区边界校验，避免租户间通过绝对路径串读文件

### `agent/protocol/agent_stream.py`

- 思考输出开关会读取当前平台 runtime context

升级关注点：

- 如果上游调整流式输出或 thinking 控制，需要重新检查平台 Agent 策略是否仍能生效

### `bridge/agent_initializer.py`

- 平台模式下按当前运行时作用域切换工作区
- 合并 Agent 自定义 `system_prompt`
- 从 Agent 独立工作区恢复会话历史
- 仅平台默认 Agent 在 tools/skills 为空时继承默认能力；自定义 Agent 空 allowlist 表示不启用对应能力
- Agent 定义的 skills allowlist 只做运行时过滤，不再反向写入 skills_config
- 平台租户模式不再把模型密钥写入全局 `~/.cow/.env`

升级关注点：

- 如果上游重构 Agent 初始化顺序，需要重新检查工作区解析和 prompt 合并逻辑
- 如果上游调整密钥初始化，需要确认平台模型配置仍只来自 runtime scope / 数据库配置，不写全局用户目录

### `bridge/agent_bridge.py`

- 支持基于 `tenant_id + agent_id + session_id` 的实例缓存键
- 运行中请求取消也使用同一 scoped key，避免相同 `session_id` 在不同租户/Agent 间互相取消
- 接入 runtime scope
- Agent cache 记录解析时的 config_version；跨进程配置变更后，下一次请求会按 DB 版本自动重建本进程缓存
- 接入 Phase 3 的 quota 校验和 usage 记录
- 平台租户模式不再把模型密钥写入全局 `~/.cow/.env`

升级关注点：

- 如果上游重构 `agent_reply()` 或消息持久化逻辑，需要重新验证 usage 与 quota 的接入点
- 如果上游调整 preemption/cancel 逻辑，需要确认取消 key 仍与 Agent 实例缓存 key 一致
- 如果上游新增 AgentBridge 缓存入口，需要接入 config_version 检查，不能只做进程内清理

### `cow_platform/services/model_config_service.py`

- 平台模式下 Agent 模型解析必须命中 DB model config；`build_legacy_model_config()` 只允许非平台 legacy 模式使用
- 平台/租户模型配置变更会 bump platform 或 tenant config_version，触发跨进程 Agent cache 失效

升级关注点：

- 如果上游新增模型配置 fallback，需要确认平台模式不会重新从 `config.py` / 环境变量拼出租户运行时模型配置

### `agent/skills/manager.py`

- 平台 runtime scope 下不再读写 workspace `skills_config.json`
- `SkillManager` 通过 `SkillConfigService` 读取/保存租户 Agent 级技能配置
- 提供 runtime-only skill enable 过滤，避免 Agent allowlist 初始化时修改持久配置

升级关注点：

- 如果上游调整 skills_config 同步逻辑，需要保留平台 DB backend 和 runtime-only allowlist 语义

### `bridge/context.py`

- `Context` 默认 kwargs 必须是每个消息独立字典，避免跨消息残留 `tenant_id` / `agent_id` / `binding_id`

升级关注点：

- 如果上游调整消息上下文对象，需要重新确认 context 状态不会跨租户消息共享

### `cow_platform/services/binding_service.py`

- 租户级外部渠道绑定必须关联本租户 `channel_config_id`
- `web` 与非平台托管入口仍保留无 `channel_config_id` 的历史绑定能力
- binding 创建、更新、删除会 bump 关联 Agent 的 runtime config_version

升级关注点：

- 如果上游新增渠道类型，需要确认该渠道是否应纳入租户级 `channel_config_id` 强约束

### `cow_platform/services/channel_config_service.py`

- 租户级渠道配置是托管渠道运行时的唯一配置来源
- 微信扫码成功后的 token / base_url / bot_id / user_id 写入租户渠道配置数据库
- 删除微信渠道配置时会清理历史默认路径下的本地凭证文件，避免旧文件在重新绑定时被误用
- 运行时覆盖不再为租户微信渠道自动注入 `weixin_credentials_path`
- 渠道配置变更会 bump channel_config runtime state，并同步 bump 已绑定 Agent 的 config_version

升级关注点：

- 如果上游新增微信登录或渠道配置字段，需要确认租户微信凭证仍以数据库为准，不能重新依赖本地 credentials json
- 如果上游调整渠道配置删除流程，需要确认删除配置后历史本地凭证不会残留复用

### `cow_platform/services/agent_service.py`

- 默认 Agent 在未配置 MCP allowlist 时继承本租户已启用的 MCP catalog
- 自定义 Agent 不继承租户 MCP catalog，只有显式绑定的 MCP server 才会进入运行时
- 平台默认 Agent 不再从 legacy `model` 配置兜底模型，运行时模型必须来自 DB model config
- Agent 创建、更新、删除会 bump 对应 Agent runtime config_version

升级关注点：

- 如果上游调整 AgentDefinition 或 MCP 解析逻辑，需要重新确认 default/custom Agent 的能力继承边界

### `channel/web/web_channel.py`

- Web 控制台强制按租户鉴权模式运行，平台不再支持关闭多租户鉴权回到全局控制台模式
- 支持显式 `agent_id`
- 支持 `binding_id -> tenant_id + agent_id` 路由
- 支持 Agent 作用域下的 sessions/history/memory/knowledge API
- Web 内部轮询队列改为 scoped session key
- 租户鉴权下将历史默认值 `tenant_id=default` 解析为当前登录租户，避免 Web 缺省参数误触发跨租户拒绝
- Route handler 已按功能拆到 `channel/web/handlers/`，`web_channel.py` 只保留 WebChannel 主类、运行时 helper 和兼容导出

升级关注点：

- 如果上游重构 web 控制台 API 或消息流处理，需要重新验证 binding 路由和 scoped queue
- 如果上游调整租户参数默认值，需要重新确认 Web 与 FastAPI 的租户 scope 解析仍一致
- 如果上游新增 Web API，优先放到对应 `channel/web/handlers/*` 模块，不要继续扩大 `web_channel.py`

### `channel/web/handlers/configuration.py`

- 多租户平台模式下 `/config` 的写入落到 PostgreSQL `platform_settings`，不再写项目根目录 `config.json`

升级关注点：

- 如果上游调整 Web 配置接口，需要确认平台模式下仍不触碰根 `config.json`

### `channel/web/frontend_layout.py`

- Web 前端入口路径集中在该文件解析
- modern 前端固定使用 `channel/web/frontend/modern/dist`
- legacy 静态前端文件已删除，运行时不再保留旧版页面入口

升级关注点：

- 如果上游调整 Web 静态资源目录或路由，需要先复核这里的前端路径解析
- 如果上游重新引入旧静态页面，需要确认平台运行时仍不会绕过 modern 前端的租户鉴权与租户渠道配置入口

### `channel/channel.py`

- Channel 基类增加 `channel_config_id`、`tenant_id`、`config_overrides`
- 托管渠道实例通过这些字段携带租户运行时配置

升级关注点：

- 如果上游调整 Channel 生命周期或字段初始化，需要重新确认托管渠道仍能注入平台上下文

### `channel/chat_channel.py`

- ChatChannel 支持按 `binding_id` 或渠道身份解析目标 Agent
- 消息 context 会注入 `binding_id`、`tenant_id`、`agent_id`、租户用户身份和 config overrides
- 对带 `channel_config_id` / `source_tenant_id` 的托管渠道强制重新解析绑定；解析不到或租户不一致时 fail-closed，禁止落回 legacy/global Agent
- preemption 取消 key 按 `tenant_id + agent_id + session_id` 生成，避免跨租户同 session_id 互相取消

升级关注点：

- 如果上游调整终端/聊天通道消息上下文，需要重新验证 binding 解析和身份映射
- 如果上游调整消息排队/取消逻辑，需要重新验证 scoped cancel key

### `agent/tools/scheduler/*`

- scheduler 在平台数据库可用时使用 `platform_scheduled_tasks`，不再以 `tasks.json` 作为平台任务真源
- 任务创建时写入 `tenant_id`、`agent_id`、`binding_id`、`channel_config_id`、`session_id`
- 调度执行时把任务作用域重新注入 Context，并按 `channel_config_id` 激活渠道运行时覆盖
- legacy JSON store 保留为数据库不可用时的兼容回退

升级关注点：

- 如果上游调整 scheduler tool/service，需要重新确认任务 CRUD、到期执行和发送结果都带租户/Agent/channel scope

### `channel/web/handlers/workspace.py`

- Scheduler API 在平台模式下读取 scoped DB task store，避免页面任务列表跨租户/Agent 泄露

升级关注点：

- 如果上游调整 workspace handler，需要确认 `/api/scheduler` 不再直接拼工作区 `scheduler/tasks.json`

### `common/cloud_client.py`

- 平台租户模式下禁止远程配置回写项目根目录 `config.json`

升级关注点：

- 如果上游调整 LinkAI/cloud 配置同步，需要确认平台模式不会重新写根 `config.json`

### `plugins/plugin_manager.py`

- 平台租户模式禁用 legacy 插件事件总线，不再读取 `plugins/plugins.json`、`plugins/config.json` 或扫描插件目录
- `emit_event()` 在平台模式下直接透传事件上下文，避免全局插件实例影响不同租户
- legacy 插件启停、安装、更新、卸载在平台模式下返回禁用提示；平台能力统一走 Agent tools / skills / MCP

升级关注点：

- 如果上游调整插件系统，需要确认平台模式仍不会加载全局插件配置或全局插件实例

### `channel/qq/qq_channel.py`

- 平台托管运行时会向消息 context 注入 `channel_config_id` 与 `source_tenant_id`

升级关注点：

- 如果上游调整 QQ 消息构造流程，需要重新挂回租户渠道上下文

### `channel/weixin/weixin_channel.py`

- 平台托管运行时会向消息 context 注入 `channel_config_id` 与 `source_tenant_id`
- 平台托管微信运行时只读取数据库中的租户渠道 token，不再从本地 credentials json 回退加载
- 会话失效处理会清空租户渠道配置数据库中的微信凭证，重新绑定只能通过 Web 渠道页面扫码

升级关注点：

- 如果上游调整微信消息构造流程，需要重新挂回租户渠道上下文
- 如果上游调整微信扫码或重登录流程，需要确认平台托管渠道不会重新写入或读取全局本地凭证文件

### `channel/wecom_bot/wecom_bot_channel.py`

- 平台托管运行时会向消息 context 注入 `channel_config_id` 与 `source_tenant_id`

升级关注点：

- 如果上游调整企微机器人消息构造流程，需要重新挂回租户渠道上下文

### `channel/feishu/feishu_channel.py`

- 平台托管运行时会向消息 context 注入 `channel_config_id` 与 `source_tenant_id`

升级关注点：

- 如果上游调整飞书消息构造流程，需要重新挂回租户渠道上下文

### `channel/dingtalk/dingtalk_channel.py`

- 群消息在租户绑定解析失败返回空 context 时必须停止后续处理，避免重新落回异常路径

升级关注点：

- 如果上游调整钉钉群消息处理流程，需要重新确认空 context 不会继续访问

### `tests/conftest.py`

- PostgreSQL 集成测试默认禁止清空平台表
- 只有显式设置 `COW_PLATFORM_TEST_RESET_DATABASE=1` 且数据库名包含 `test` 时，才允许测试清理专用测试库

升级关注点：

- 如果上游调整测试夹具，必须保留“真实平台库不可被测试清空”的保护

### `channel/web/frontend/modern/`

- 平台 Web 控制台的 React + TypeScript + Vite 前端源码
- `/chat` 由 `channel/web/frontend_layout.py` 固定渲染 `frontend/modern/dist/index.html`
- `/assets/*` 仅从 `frontend/modern/dist/` 解析构建产物
- 外部渠道 binding 表单按租户渠道配置过滤，并要求非 Web 绑定选择 `channel_config_id`

升级关注点：

- 如果上游调整 Web 控制台入口，需要重新确认 modern 前端构建目录和 `/assets/*` 路由仍一致
- 如果上游重构渠道接入页面，需要重新验证外部渠道绑定不能保存为空 `channel_config_id`

### `pyproject.toml`

- 把 `cow_platform*` 纳入打包发现范围

升级关注点：

- 如果上游调整打包方式，需要确认 platform 模块仍会被安装

### `cli/commands/platform.py`

- 新增 `cow platform` 治理、doctor、worker、channel-runtime、migrate 相关命令

升级关注点：

- 如果上游调整 CLI 命令加载方式，需要确认 platform 命令仍能注册

### `docker/entrypoint.sh`

- 支持平台 API / worker 等部署入口
- 平台 Docker 启动只使用环境变量和 PostgreSQL migration，不再生成或修改根目录 `config.json`

升级关注点：

- 如果上游调整容器启动脚本，需要重新确认平台 API / worker / Web 控制台能按数据库配置启动，且不会重新依赖根 `config.json`

### `docker/Dockerfile.latest`

- 平台镜像构建不再从 `config-template.json` 复制生成根 `config.json`
- 多租户 Docker 部署的启动配置来自 compose 环境变量，运行时配置来自 PostgreSQL

### `docker/compose.platform.yml`

- 定义平台 API、job worker、channel runtime worker、Web 控制台、PostgreSQL 等运行组件
- `platform-web` 显式设置 `COW_PLATFORM_START_CHANNEL_RUNTIMES=false`，避免 Web 进程承载租户长连接/轮询渠道

升级关注点：

- 如果上游调整 compose 文件组织方式，需要重新确认平台部署文件不被覆盖，且 `platform-channel-runtime` 仍与 `platform-web` 分离

## 使用方式

吸收上游更新前：

1. 先阅读本文档，确认 patch 触点
2. 合并上游后，逐个检查这些文件是否有冲突或语义变化
3. 重新跑全量测试
4. 对 patch 清单做增删修订
