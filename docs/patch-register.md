# Patch Register

本文档记录平台化过程中，对原有 CoreAgent 上游文件做过的兼容修改。
目标不是把所有变更都记在这里，而是把“未来升级时最容易冲突的 patch 点”明确下来。

当前二开基线把上游 CoreAgent 作为 Agent 内核，平台能力优先落在 `cow_platform/`。
上游参考版本：<https://github.com/zhayujie/CoreAgent/tree/2.0.7>

## Patch 清单

### `app.py`

- 平台模式启动入口只负责加载配置、启动 Web 控制台和注册信号处理
- `ChannelManager` 已抽离到 `cow_platform/runtime/channel_manager.py`，`app.py` 仅保留兼容导出
- 本地源码直接执行 `python app.py` 时会自动加载 `.env.local`，让端口、数据库、Redis、Qdrant、MinIO、模型和工作区与 `scripts/start-platform-local.sh` 保持一致；可用 `COW_PLATFORM_AUTO_LOCAL_ENV=false` 关闭

升级关注点：

- 如果上游调整应用启动，需要确认 Web 进程不会重新默认承载长连接/轮询渠道
- 如果上游调整 ChannelManager，需要合并到平台 runtime 层，不要重新塞回 `app.py`
- 如果上游调整启动配置加载顺序，需要确认直接执行 `python app.py` 仍不会退回 Docker 端口 `9899` 或错误数据库凭据

### `config.py`

- `Config.get()` / `Config.__getitem__()` 会优先读取当前 runtime scope 中的配置覆盖
- 平台托管渠道运行时通过该覆盖机制注入模型、渠道密钥等租户级配置
- 平台模式不读取项目根目录 `config.json` / `config-template.json`，启动层来自环境变量，平台运行时配置来自 PostgreSQL `platform_settings`
- 数据库平台设置会覆盖内存配置，并同步到环境变量供子进程使用，避免旧环境变量压过平台数据库配置
- 平台租户模式不再读取或保存全局 `user_datas.pkl`，运行期 `get_user_data()` 也返回 no-op 视图，避免不同租户的外部用户 ID 复用 legacy 用户级模型/API key
- `platform_start_channel_runtimes` 默认关闭，用于把 Web 进程与租户渠道 runtime worker 解耦
- `build_config_environment()` 统一生成子进程/Skill 运行时环境变量，平台 runtime scope 与数据库配置优先于宿主环境变量
- 吸收 2.0.7 `skill` 配置结构，平台图像生成能力通过 `skill.image-generation.model` 注入内置 Skill

升级关注点：

- 如果上游调整全局配置读取方式，需要重新确认优先级仍是 runtime scope > platform_settings > environment > 内置默认值
- 如果上游重新引入用户级 legacy 配置持久化，需要确认平台模式不会落回全局 pickle 文件或全局内存字典
- 如果上游新增 Skill 运行脚本所需环境变量，需要统一接入 `build_config_environment()`，不要在调用点重复拼环境变量

### `cow_platform/runtime/environment.py`

- 平台子进程环境的统一构造入口，合并宿主环境、当前 runtime scope、显式覆盖和调用点额外变量
- `bash` 工具和平台图像生成服务都复用该入口，避免各自重复拼接密钥、base URL 和 Skill env

升级关注点：

- 如果上游新增子进程型工具或 Skill 执行入口，应优先复用 `build_runtime_environment()`，不要在核心通道或工具内重新拼平台环境变量

### `cow_platform/db/postgres.py`

- 平台 PostgreSQL 访问增加连接池，减少高频仓储调用反复建连的开销
- 增加版本化 migration runner 和 `platform_schema_migrations` 迁移登记表，容器启动、CLI 与测试共用同一套 schema 入口
- 增加 `platform_scheduled_tasks` 表，作为定时任务在平台模式下的唯一配置真源
- 增加 `platform_channel_runtime_leases` 表，作为托管渠道运行时的分布式所有权记录
- 增加 `platform_runtime_state` 表，作为 runtime desired state、config_version 和 invalidation 的统一真源
- 增加 `platform_skill_configs` 表，作为平台模式下 skills_config 的租户/Agent 级配置真源
- `platform_memory_chunks` 在 pgvector 可用时增加 `embedding_vector` 和 HNSW 索引；pgvector 不可用时保留 JSONB embedding 回退
- `platform_conversation_messages.metadata` 记录消息级运行状态，例如当轮是否开启 `enable_thinking`

升级关注点：

- 如果上游调整数据库初始化方式，需要确认平台连接池、版本化 migration、调度任务表、runtime state、技能配置、渠道运行时 lease 表和 memory vector schema 仍会初始化

### `cow_platform/runtime/channel_manager.py`

- 平台 ChannelManager 的唯一实现位置，负责本地 Web channel、租户托管渠道、lease、heartbeat、singleton cache 清理和运行时配置覆盖
- `app.py` 与 `cow_platform/worker/channel_runtime.py` 都引用该模块，避免 Web 入口和 runtime worker 各自维护一套渠道生命周期逻辑

升级关注点：

- 如果上游调整渠道生命周期，需要确认托管渠道仍按 `channel_config_id` 获取 lease 后才能启动
- 如果上游新增渠道 singleton 或启动约束，需要在这里统一维护，不要分散到 `app.py` 或 Web handler

### `cow_platform/runtime/channel_target_resolver.py`

- 托管渠道消息的外部身份、binding、tenant user 解析集中在该 runtime 模块
- `ChatChannel` 只委托解析结果，不直接导入 binding / tenant user service，避免核心通道继续膨胀

升级关注点：

- 如果上游调整渠道消息字段，需要先更新这里的身份抽取和 fail-closed 策略，再验证所有非 Web 托管渠道

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

### `scripts/start-platform-local.sh`

- 本地源码启动平台 Web 时，同时编排已有 `cow_platform.worker.channel_runtime`，保持本地调试也具备租户渠道消息消费能力
- 仅启动已有 runtime worker，不在脚本内复制渠道解析、binding 或消息处理逻辑；可用 `START_CHANNEL_RUNTIME=false` 临时关闭

升级关注点：

- 如果上游调整本地启动脚本，需要确认 `app.py` 仍只承担 Web/API，租户渠道仍通过独立 runtime worker 消费消息

### `cow_platform/services/scheduler_task_store.py`

- 新增 DB-backed scheduler task store，所有任务按 `tenant_id + agent_id + task_id` 隔离
- 工具/UI 使用 scoped store，只能读写当前租户和 Agent 的任务；后台调度使用 unscoped store 扫描到期任务

升级关注点：

- 如果上游调整 scheduler 存储接口，需要保留 tenant/agent scope，不能重新把任务写回全局 `tasks.json`

### `cow_platform/runtime/scheduler_runtime.py`

- 平台 scheduler 的 DB store 创建、任务 scope 解析、渠道 runtime overrides 和结果派发集中在该模块
- `agent/tools/scheduler/integration.py` 只保留调度执行编排；legacy JSON 回退放在 `agent/tools/scheduler/legacy_runtime.py`

升级关注点：

- 如果上游调整 scheduler 执行链路，需要保留平台 runtime 派发边界，避免重新在 integration 里拼 DB/channel 平台细节

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
- 会话历史读取优先按 assistant 消息的 `metadata.enable_thinking` 决定是否返回 reasoning/thinking 内容；旧消息无消息级标记时再回退全局 `enable_thinking`

升级关注点：

- 如果上游调整会话存储实现，需要重新确认多 Agent 隔离是否仍然成立
- 如果上游调整 thinking 存储字段，需要确认关闭展示时不会把推理内容回放到 Web 历史

### `agent/memory/storage.py`

- 长期记忆存储使用平台 Agent 工作区路径派生隔离命名空间
- embedding 写入优先同步到 PostgreSQL `vector` 列，向量搜索优先走 pgvector 距离排序
- 当 pgvector 扩展、列或索引不可用时保留 JSONB embedding + Python cosine 回退，避免部署环境缺扩展导致 memory 功能不可用

升级关注点：

- 如果上游重构长期记忆索引路径，需要重新确认租户/Agent 工作区不会串用，且向量搜索不会退回全表 JSON 扫描作为唯一生产路径

### `agent/memory/manager.py`

- `MemoryManager` 支持禁用宿主环境变量 embedding fallback，平台租户模式由 `AgentInitializer` 显式传入 embedding provider
- 当 `OPENAI_API_BASE` 指向具体端点而不是 OpenAI-compatible API base 时跳过 env embedding，避免拼接 `/embeddings` 形成无效请求

升级关注点：

- 如果上游调整 MemoryManager embedding 初始化，需要确认平台模式不会重新读取宿主 `OPENAI_API_KEY` / `OPENAI_API_BASE`
- 如果上游新增 embedding provider fallback，需要先确认它不会绕过租户 runtime scope 和平台数据库配置

### `agent/tools/*`

- 文件类工具统一限制在当前 Agent 工作区内访问，绝对路径、`~` 路径或 `..` 越界路径不能读取/写入其他租户工作区
- `bash` 工具运行目录仍是当前 Agent 工作区，并在执行前拦截明显的跨工作区路径访问；大输出临时文件也保存到当前工作区 `tmp/`
- 内置 Skill 仍位于项目 `skills/` 目录；`read` 只允许越界读取内置 `SKILL.md`，`bash` 只允许内置 `scripts/` 脚本作为 Skill 执行入口，不能放开项目源码目录
- `bash` 工具执行 Skill 脚本前通过 `build_runtime_environment()` 注入平台 runtime 配置，避免子进程读取旧的宿主环境变量

升级关注点：

- 如果上游调整 `read/write/edit/ls/send/bash` 或新增文件访问类工具，需要重新接入工作区边界校验，避免租户间通过绝对路径串读文件
- 如果上游新增需要子进程运行的工具，需要复用统一环境构造逻辑，避免平台 DB 配置和 legacy env 分叉

### `agent/protocol/agent_stream.py`

- 思考输出开关会读取当前平台 runtime context
- 默认不展示 thinking/reasoning；开启时只清理 `<think>` 标签但保留内容，关闭时过滤整段 thinking 输出
- 空响应重试保留工具调用结果，避免模型先返回空文本但带 `tool_calls` 时被错误降级为 fallback
- Gemini 原生多模态/tool call 的原始 parts 会随 assistant 消息保存，供下一轮 Gemini 请求恢复

升级关注点：

- 如果上游调整流式输出或 thinking 控制，需要重新检查平台 Agent 策略是否仍能生效
- 如果上游调整空响应重试、工具调用或 Gemini parts 结构，需要确认平台流式协议不会丢失 tool_calls / native parts

### `agent/chat/session_service.py`

- 仅吸收 2.0.7 会话标题生成辅助函数，Web 会话生命周期仍保留在平台既有 handler / store 路径
- 不引入上游完整 `SessionService` 类，避免和平台 tenant/agent/binding aware 会话管理形成第二套生命周期逻辑

升级关注点：

- 如果上游继续扩展会话服务，需要优先提取可复用纯函数；会话创建、更新、分页仍应落在平台现有 scoped handler

### `bridge/agent_initializer.py`

- 平台模式下按当前运行时作用域切换工作区
- 合并 Agent 自定义 `system_prompt`
- 从 Agent 独立工作区恢复会话历史
- 仅平台默认 Agent 在 tools/skills 为空时继承默认能力；自定义 Agent 空 allowlist 表示不启用对应能力
- Agent 定义的 skills allowlist 只做运行时过滤，不再反向写入 skills_config
- 平台租户模式不再把模型密钥写入全局 `~/.cow/.env`
- 平台租户模式不再读取全局 `~/.cow/.env`，避免宿主机旧 `OPENAI_API_BASE` 等变量污染当前租户运行时
- 平台租户模式下长期记忆索引同步改为后台去重执行，避免首轮 Agent 回复被 memory sync 阻塞
- 平台租户模式下 MCP server 改为 Agent 创建后后台预热，避免 MCP 启动和工具枚举阻塞上游 Agent 首轮模型调用
- 相同 MCP server 解析配置在 Web 进程内复用同一个 `MCPManager`，每个 Agent 只创建轻量 `MCPTool` wrapper，避免每个会话重复启动相同 MCP 子进程

升级关注点：

- 如果上游重构 Agent 初始化顺序，需要重新检查工作区解析和 prompt 合并逻辑
- 如果上游调整密钥初始化，需要确认平台模型配置仍只来自 runtime scope / 数据库配置，不写全局用户目录
- 如果上游调整 memory 或 MCP 初始化，需要确认平台模式仍不把 memory sync / MCP start 放回首轮同步路径，且不要重新变成按会话启动重复 MCP 进程

### `bridge/agent_bridge.py`

- 支持基于 `tenant_id + agent_id + session_id` 的实例缓存键
- 运行中请求取消也使用同一 scoped key，避免相同 `session_id` 在不同租户/Agent 间互相取消
- 接入 runtime scope
- Agent cache 记录解析时的 config_version；跨进程配置变更后，下一次请求会按 DB 版本自动重建本进程缓存
- 通过 `AgentGovernanceService` 接入 Phase 3 的 quota 校验和 usage 记录，AgentBridge 不直接拼计费/用量细节
- 文件回复构造集中到 `bridge/file_reply.py`，AgentBridge 只保留兼容 wrapper
- AgentLLMModel 复用 Bridge 的 chat bot cache，避免每个会话新建底层模型 Bot 而偏离上游执行路径
- 会话消息持久化集中到 `agent/memory/conversation_persistence.py`，避免 AgentBridge 与 ChatService 各自维护一套追加逻辑
- 平台租户模式不再把模型密钥写入全局 `~/.cow/.env`

升级关注点：

- 如果上游重构 `agent_reply()` 或消息持久化逻辑，需要重新验证 usage 与 quota 的接入点
- 如果上游新增文件发送或会话持久化分支，需要优先复用 `bridge/file_reply.py` 和 `agent/memory/conversation_persistence.py`
- 如果上游调整 preemption/cancel 逻辑，需要确认取消 key 仍与 Agent 实例缓存 key 一致
- 如果上游新增 AgentBridge 缓存入口，需要接入 config_version 检查，不能只做进程内清理

### `cow_platform/services/model_config_service.py`

- 平台模式下 Agent 模型解析必须命中 DB model config；`build_legacy_model_config()` 只允许非平台 legacy 模式使用
- 平台/租户模型配置变更会 bump platform 或 tenant config_version，触发跨进程 Agent cache 失效
- 吸收 2.0.7 新模型枚举时，同步更新平台模型列表，避免 Web 端可选模型和运行时模型常量不一致

升级关注点：

- 如果上游新增模型配置 fallback，需要确认平台模式不会重新从 `config.py` / 环境变量拼出租户运行时模型配置

### `cow_platform/services/capability_config_service.py`

- 平台模型能力配置继续作为文生图/语音/多模态等能力路由的真源
- 文生图能力在构造 runtime overrides 时同步写入 `skill.image-generation.model`，由 2.0.7 内置图像生成 Skill 执行

升级关注点：

- 如果上游新增或调整图像生成 Skill 配置字段，需要先接到 capability service，再由平台图像生成服务统一调用 Skill，不能恢复多套文生图执行路径

### `cow_platform/services/vision_capability_service.py`

- 平台多模态能力解析集中在该服务，负责从 runtime context 找到 `multimodal` capability 并转换为 Vision provider 配置
- `agent/tools/vision/vision.py` 只负责 Vision 工具协议和 provider 调用，不再直接查询 capability service 或 provider 映射

升级关注点：

- 如果上游调整 Vision 工具或新增多模态厂商，优先更新该服务和 capability provider 映射，避免工具内部再次出现平台 DB 查询逻辑

### `cow_platform/services/image_generation_service.py`

- 平台 capability 文生图的唯一执行服务，负责调用 2.0.7 `skills/image-generation` 脚本、解析输出和转换错误
- 使用 `build_runtime_environment()` 注入租户模型、URL、key、Skill model 和输出目录
- `ChatChannel` 只负责判断是否命中平台 capability，并把服务结果转换为通道 Reply

升级关注点：

- 如果上游调整图像生成 Skill 入参、输出协议或错误格式，只修改该服务和对应测试，不要把 subprocess/env 逻辑放回 `channel/chat_channel.py`

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
- 平台 service factory 和渠道 runtime 刷新逻辑集中到 `channel/web/service_registry.py`，`web_channel.py` 保留兼容 wrapper 供 handler 和测试注入
- Cookie、token、登录、注册和鉴权响应构造集中到 `channel/web/auth_runtime.py`，`web_channel.py` 保留兼容 wrapper
- SSE `/stream` 建连后立即发送注释帧，避免浏览器等待首个 1s keepalive 才认为 stream 已打开

升级关注点：

- 如果上游重构 web 控制台 API 或消息流处理，需要重新验证 binding 路由和 scoped queue
- 如果上游调整租户参数默认值，需要重新确认 Web 与 FastAPI 的租户 scope 解析仍一致
- 如果上游新增 Web API，优先放到对应 `channel/web/handlers/*` 模块，不要继续扩大 `web_channel.py`
- 如果上游新增 Web 侧平台服务依赖，优先放到 service registry，不要在 `web_channel.py` 顶层散落 service import
- 如果上游调整 Web 鉴权流程，应合并到 `auth_runtime.py`，不要在 route handler 或 WebChannel 里重新拼 token/cookie 逻辑
- 如果上游调整 SSE 生成器，需要确认建连首帧不回退到固定 1s 空等

### `channel/web/handlers/configuration.py`

- 多租户平台模式下 `/config` 的写入落到 PostgreSQL `platform_settings`，不再写项目根目录 `config.json`
- `enable_thinking` 默认关闭，与平台 Agent 策略、内核流式协议和 modern 前端默认值保持一致

升级关注点：

- 如果上游调整 Web 配置接口，需要确认平台模式下仍不触碰根 `config.json`
- 如果上游重新修改 thinking 默认值，需要同时复核 configuration handler、Web chat 请求和前端配置页

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
- Web 等交互通道入队后通过事件唤醒消费线程，避免新消息最长等待固定 200ms 轮询间隔
- 平台 capability 文生图统一委托 `cow_platform/services/image_generation_service.py`，避免在核心通道内保留 subprocess/env 细节
- 托管渠道 binding 和租户用户解析委托 `cow_platform/runtime/channel_target_resolver.py`，核心通道不直接依赖平台 service

升级关注点：

- 如果上游调整终端/聊天通道消息上下文，需要重新验证 binding 解析和身份映射
- 如果上游调整消息排队/取消逻辑，需要重新验证 scoped cancel key 和入队事件唤醒，避免回退到固定轮询延迟
- 如果上游调整图像生成 Skill 输出协议，应更新平台图像生成服务和对应测试，不要新增第二套执行逻辑

### `agent/tools/scheduler/*`

- scheduler 在平台数据库可用时使用 `platform_scheduled_tasks`，不再以 `tasks.json` 作为平台任务真源
- 任务创建时写入 `tenant_id`、`agent_id`、`binding_id`、`channel_config_id`、`session_id`
- 调度执行时把任务作用域重新注入 Context，并按 `channel_config_id` 激活渠道运行时覆盖
- legacy JSON store 保留为数据库不可用时的兼容回退
- `skill_call` 执行完成后必须通过统一渠道派发结果，避免任务执行成功但用户收不到消息

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
- 吸收 2.0.7 Web 优化时只改 modern 前端：聊天区智能滚动、reasoning 渲染上限、知识库根文件/多级目录展示和能力配置图像生成选项
- ChatPage 的会话 ID、scope storage key 和会话列表分组逻辑抽到 `src/chat/sessionState.tsx`，页面组件只保留交互编排

升级关注点：

- 如果上游调整 Web 控制台入口，需要重新确认 modern 前端构建目录和 `/assets/*` 路由仍一致
- 如果上游重构渠道接入页面，需要重新验证外部渠道绑定不能保存为空 `channel_config_id`
- 如果上游更新旧静态 UI，不要恢复 legacy 静态前端；对应能力应迁移到 modern 前端

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
