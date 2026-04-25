/* =====================================================================
   CowAgent Console - Main Application Script
   ===================================================================== */

// =====================================================================
// Version — fetched from backend (single source: /VERSION file)
// =====================================================================
let APP_VERSION = '';

// =====================================================================
// i18n
// =====================================================================
const I18N = {
    zh: {
        console: '控制台',
        nav_chat: '对话', nav_manage: '管理', nav_monitor: '监控',
        menu_chat: '对话', menu_config: '配置', menu_skills: '技能',
        menu_memory: '记忆', menu_knowledge: '知识', menu_channels: '通道', menu_tasks: '定时',
        menu_logs: '日志', menu_agents: '智能体', menu_bindings: '绑定',
        menu_tenants: '租户', menu_tenant_users: '租户用户',
        knowledge_title: '知识库', knowledge_desc: '浏览和探索你的知识库',
        knowledge_tab_docs: '文档', knowledge_tab_graph: '图谱',
        knowledge_loading: '加载知识库中...', knowledge_loading_desc: '知识页面将显示在这里',
        knowledge_select_hint: '选择一个文档查看', knowledge_empty_hint: '暂无知识页面',
        knowledge_empty_guide: '在对话中发送文档、链接或主题给 Agent，它会自动整理到你的知识库中。',
        knowledge_go_chat: '开始对话',
        welcome_subtitle: '我可以帮你解答问题、管理计算机、创造和执行技能，并通过<br>长期记忆和知识库不断成长',
        example_sys_title: '系统管理', example_sys_text: '查看工作空间里有哪些文件',
        example_task_title: '定时任务', example_task_text: '1分钟后提醒我检查服务器',
        example_code_title: '编程助手', example_code_text: '搜索AI资讯并生成可视化网页报告',
        example_knowledge_title: '知识库', example_knowledge_text: '查看知识库当前文档情况',
        example_skill_title: '技能系统', example_skill_text: '查看所有支持的工具和技能',
        example_web_title: '指令中心', example_web_text: '查看全部命令',
        input_placeholder: '输入消息，或输入 / 使用指令',
        config_title: '配置管理', config_desc: '管理模型和 Agent 配置',
        config_model: '模型配置', config_agent: 'Agent 配置',
        config_channel: '通道配置',
        config_agent_enabled: 'Agent 模式',
        config_max_tokens: '最大上下文 Token', config_max_tokens_hint: '对话中 Agent 能输入的最大 Token 长度，超过后会智能压缩处理',
        config_max_turns: '最大记忆轮次', config_max_turns_hint: '一问一答为一轮，超过后会智能压缩处理',
        config_max_steps: '最大执行步数', config_max_steps_hint: '单次对话中 Agent 最多调用工具的次数',
        config_enable_thinking: '深度思考', config_enable_thinking_hint: '启用后在 Web 端展示模型推理过程',
        config_channel_type: '通道类型',
        config_provider: '模型厂商', config_model_name: '模型',
        config_custom_model_hint: '输入自定义模型名称',
        config_save: '保存', config_saved: '已保存',
        config_save_error: '保存失败',
        config_custom_option: '自定义...',
        config_security: '安全设置', config_password: '访问密码',
        config_password_hint: '留空则不启用密码保护',
        config_password_changed: '密码已更新，请重新登录',
        config_password_cleared: '密码已清除',
        skills_title: '技能管理', skills_desc: '查看、启用或禁用 Agent 技能', skills_hub_btn: '探索技能广场',
        skills_loading: '加载技能中...', skills_loading_desc: '技能加载后将显示在此处',
        tools_section_title: '内置工具', tools_loading: '加载工具中...',
        skills_section_title: '技能', skill_enable: '启用', skill_disable: '禁用',
        skill_toggle_error: '操作失败，请稍后再试',
        memory_title: '记忆管理', memory_desc: '查看 Agent 记忆文件和内容',
        memory_tab_files: '记忆文件', memory_tab_dreams: '梦境日记',
        memory_loading: '加载记忆文件中...', memory_loading_desc: '记忆文件将显示在此处',
        memory_back: '返回列表',
        memory_col_name: '文件名', memory_col_type: '类型', memory_col_size: '大小', memory_col_updated: '更新时间',
        channels_title: '通道管理', channels_desc: '管理已接入的消息通道',
        channels_add: '接入通道', channels_disconnect: '断开',
        channels_save: '保存配置', channels_saved: '已保存', channels_save_error: '保存失败',
        channels_restarted: '已保存并重启',
        channels_connect_btn: '接入', channels_cancel: '取消',
        channels_select_placeholder: '选择要接入的通道...',
        channels_empty: '暂未接入任何通道', channels_empty_desc: '点击右上角「接入通道」按钮开始配置',
        channels_disconnect_confirm: '确认断开该通道？配置将保留但通道会停止运行。',
        channels_connected: '已接入', channels_connecting: '接入中...',
        weixin_scan_title: '微信扫码登录', weixin_scan_desc: '请使用微信扫描下方二维码',
        weixin_scan_loading: '正在获取二维码...', weixin_scan_waiting: '等待扫码...',
        weixin_scan_scanned: '已扫码，请在手机上确认', weixin_scan_expired: '二维码已过期，正在刷新...',
        weixin_scan_success: '登录成功，正在启动通道...', weixin_scan_fail: '获取二维码失败',
        weixin_qr_tip: '二维码约2分钟后过期',
        wecom_scan_btn: '扫码创建企微机器人', wecom_scan_desc: '使用企业微信扫码，一键创建智能机器人',
        wecom_scan_success: '创建成功，正在启动通道...',
        wecom_scan_fail: '创建失败',
        wecom_mode_scan: '扫码接入', wecom_mode_manual: '手动填写',
        tasks_title: '定时任务', tasks_desc: '查看和管理定时任务',
        tasks_coming: '即将推出', tasks_coming_desc: '定时任务管理功能即将在此提供',
        logs_title: '日志', logs_desc: '实时日志输出 (run.log)',
        logs_live: '实时', logs_coming_msg: '日志流即将在此提供。将连接 run.log 实现类似 tail -f 的实时输出。',
        new_chat: '新对话',
        session_history: '历史会话',
        today: '今天', yesterday: '昨天', earlier: '更早',
        delete_session_confirm: '确认删除该会话？所有消息将被清除。',
        delete_session_title: '删除会话',
        untitled_session: '新对话',
        context_cleared: '— 以上内容已从上下文中移除 —',
        tip_new_chat: '新建对话',
        tip_clear_context: '清除上下文',
        tip_attach_file: '上传附件',
        confirm_yes: '确认',
        confirm_cancel: '取消',
        error_send: '发送失败，请稍后再试。', error_timeout: '请求超时，请再试一次。',
        thinking_in_progress: '思考中...', thinking_done: '已深度思考', thinking_duration: '耗时',
        agents_title: '智能体管理', agents_desc: '创建、配置和管理 Agent 智能体',
        agents_create: '创建智能体', agents_edit: '编辑智能体',
        agents_loading: '加载智能体中...', agents_loading_desc: '智能体列表将显示在此处',
        agents_filter_tenant: '租户筛选', agents_refresh: '刷新',
        agents_empty: '暂无智能体', agents_empty_desc: '点击右上角「创建智能体」按钮开始',
        agents_section_basic: '基础信息', agents_section_tools: '工具配置',
        agents_section_skills: '技能配置', agents_section_knowledge: '知识库',
        agents_section_mcp: 'MCP Server',
        agents_field_tenant: '租户 ID', agents_field_id: 'Agent ID', agents_field_name: '名称',
        agents_field_id_hint: '留空自动生成（推荐）',
        agents_field_model: '模型', agents_field_prompt: '系统 Prompt',
        agents_knowledge_enabled: '启用知识库',
        agents_loading_tools: '加载工具中...', agents_loading_skills: '加载技能中...',
        agents_add_mcp: '添加 Server', agents_mcp_name: '名称',
        agents_mcp_command: '命令', agents_mcp_args: '参数',
        agents_cancel: '取消', agents_save: '保存',
        agents_delete: '删除', agents_delete_confirm: '确认删除该智能体？此操作不可撤销。',
        agents_delete_title: '删除智能体',
        agents_save_success: '保存成功', agents_save_error: '保存失败',
        agents_tools_count: '个工具', agents_skills_count: '个技能',
        agents_knowledge_on: '知识库已启用', agents_knowledge_off: '知识库未启用',
        bindings_title: 'Binding 管理',
        bindings_desc: '管理租户、渠道和 Agent 之间的路由绑定',
        bindings_create: '创建绑定',
        bindings_edit: '编辑绑定',
        bindings_loading: '加载绑定中...',
        bindings_loading_desc: '绑定列表将显示在此处',
        bindings_empty: '暂无绑定',
        bindings_empty_desc: '点击右上角「创建绑定」按钮开始',
        bindings_section_basic: '基础信息',
        bindings_section_route: '路由匹配',
        bindings_field_tenant: '租户 ID',
        bindings_field_id: 'Binding ID',
        bindings_field_name: '名称',
        bindings_field_channel: '通道类型',
        bindings_field_agent: '目标 Agent',
        bindings_field_enabled: '启用绑定',
        bindings_field_app_id: '外部应用 ID',
        bindings_field_chat_id: '外部会话 ID',
        bindings_field_user_id: '外部用户 ID',
        bindings_route_hint: '留空表示更宽泛的匹配；填写越多，渠道消息会越精确地路由到当前绑定。',
        bindings_route_any: '匹配当前通道下的所有消息',
        bindings_route_prefix: '匹配条件',
        bindings_route_app: '应用',
        bindings_route_chat: '会话',
        bindings_route_user: '用户',
        bindings_status_enabled: '已启用',
        bindings_status_disabled: '已停用',
        bindings_route_disabled: '当前绑定不会参与路由',
        bindings_cancel: '取消',
        bindings_save: '保存',
        bindings_save_error: '保存失败',
        bindings_delete: '删除',
        bindings_delete_title: '删除绑定',
        bindings_delete_confirm: '确认删除该绑定？此操作不可撤销。',
        bindings_no_agents: '当前租户下暂无可用 Agent',
        bindings_loading_agents: '加载 Agent 中...',
        tenants_title: '租户管理',
        tenants_desc: '创建和维护多租户资源边界',
        tenants_create: '创建租户',
        tenants_edit: '编辑租户',
        tenants_loading: '加载租户中...',
        tenants_loading_desc: '租户列表将显示在此处',
        tenants_empty: '暂无租户',
        tenants_empty_desc: '点击右上角「创建租户」按钮开始',
        tenants_field_id: '租户 ID',
        tenants_field_name: '名称',
        tenants_field_status: '状态',
        tenants_save: '保存',
        tenants_cancel: '取消',
        tenants_save_error: '保存失败',
        tenants_delete_title: '删除租户',
        tenants_delete_confirm: '确认删除该租户？该操作风险较高。',
        tenant_users_title: '租户角色管理',
        tenant_users_desc: '管理租户下用户、角色和状态',
        tenant_users_create: '新增用户',
        tenant_users_edit: '编辑用户',
        tenant_users_loading: '加载租户用户中...',
        tenant_users_loading_desc: '租户用户列表将显示在此处',
        tenant_users_empty: '暂无租户用户',
        tenant_users_empty_desc: '点击右上角「新增用户」按钮开始',
        tenant_users_filter_tenant: '租户筛选',
        tenant_users_refresh: '刷新',
        tenant_users_field_tenant: '租户 ID',
        tenant_users_field_user_id: '用户 ID',
        tenant_users_field_name: '名称',
        tenant_users_field_role: '角色',
        tenant_users_field_status: '状态',
        tenant_users_save: '保存',
        tenant_users_cancel: '取消',
        tenant_users_save_error: '保存失败',
        tenant_users_delete_title: '删除租户用户',
        tenant_users_delete_confirm: '确认删除该租户用户？',
        tenant_users_no_tenants: '暂无租户，请先创建租户',
        tenant_users_load_meta_error: '无法加载角色定义',
        menu_mcp: 'MCP',
        mcp_title: 'MCP 服务管理', mcp_desc: '管理 Model Context Protocol 服务器连接',
        mcp_add_server: '添加服务器', mcp_server_name: '服务器名称',
        mcp_command: '启动命令', mcp_args: '参数',
        mcp_env: '环境变量', mcp_add_env: '添加变量',
        mcp_test_connection: '测试连接', mcp_tools_provided: '提供的工具',
        mcp_no_servers: '暂无 MCP 服务器', mcp_no_servers_desc: '点击右上角「添加服务器」按钮开始',
        mcp_loading: '加载 MCP 服务器中...', mcp_loading_desc: 'MCP 服务器列表将显示在此处',
        mcp_select_agent: '选择智能体', mcp_test_success: '连接成功', mcp_test_failed: '连接失败',
        mcp_test_testing: '测试中...', mcp_tools_found: '发现 {n} 个工具',
        mcp_delete: '删除', mcp_delete_confirm: '确认删除该 MCP 服务器？', mcp_delete_title: '删除 MCP 服务器',
        mcp_save: '保存', mcp_cancel: '取消',
        mcp_save_success: '保存成功', mcp_save_error: '保存失败',
        mcp_view_tools: '查看工具', mcp_hide_tools: '收起工具',
        mcp_env_key: '变量名', mcp_env_value: '变量值',
        mcp_edit: '编辑', mcp_edit_server: '编辑服务器',
        mcp_no_tools: '暂无工具信息', mcp_name_required: '服务器名称不能为空',
        mcp_command_required: '启动命令不能为空',
    },
    en: {
        console: 'Console',
        nav_chat: 'Chat', nav_manage: 'Management', nav_monitor: 'Monitor',
        menu_chat: 'Chat', menu_config: 'Config', menu_skills: 'Skills',
        menu_memory: 'Memory', menu_knowledge: 'Knowledge', menu_channels: 'Channels', menu_tasks: 'Tasks',
        menu_logs: 'Logs', menu_agents: 'Agents', menu_bindings: 'Bindings',
        menu_tenants: 'Tenants', menu_tenant_users: 'Tenant Users',
        knowledge_title: 'Knowledge', knowledge_desc: 'Browse and explore your knowledge base',
        knowledge_tab_docs: 'Documents', knowledge_tab_graph: 'Graph',
        knowledge_loading: 'Loading knowledge base...', knowledge_loading_desc: 'Knowledge pages will be displayed here',
        knowledge_select_hint: 'Select a document to view', knowledge_empty_hint: 'No knowledge pages yet',
        knowledge_empty_guide: 'Send documents, links or topics to the agent in chat, and it will automatically organize them into your knowledge base.',
        knowledge_go_chat: 'Start a conversation',
        welcome_subtitle: 'I can help you answer questions, manage your computer, create and execute skills, and keep growing through <br> long-term memory and a personal knowledge base.',
        example_sys_title: 'System', example_sys_text: 'Show me the files in the workspace',
        example_task_title: 'Scheduler', example_task_text: 'Remind me to check the server in 5 minutes',
        example_code_title: 'Coding', example_code_text: 'Search today\'s AI news and generate a visual report webpage',
        example_knowledge_title: 'Knowledge', example_knowledge_text: 'Show me the current knowledge base',
        example_skill_title: 'Skills', example_skill_text: 'Show current tools and skills',
        example_web_title: 'Commands', example_web_text: 'Show all commands',
        input_placeholder: 'Type a message, or press / for commands',
        config_title: 'Configuration', config_desc: 'Manage model and agent settings',
        config_model: 'Model Configuration', config_agent: 'Agent Configuration',
        config_channel: 'Channel Configuration',
        config_agent_enabled: 'Agent Mode',
        config_max_tokens: 'Max Context Tokens', config_max_tokens_hint: 'Max tokens the Agent can input per conversation, auto-compressed when exceeded',
        config_max_turns: 'Max Memory Turns', config_max_turns_hint: 'One Q&A pair = one turn, auto-compressed when exceeded',
        config_max_steps: 'Max Steps', config_max_steps_hint: 'Max tool calls the Agent can make in a single conversation',
        config_enable_thinking: 'Deep Thinking', config_enable_thinking_hint: 'Show model reasoning on web console',
        config_channel_type: 'Channel Type',
        config_provider: 'Provider', config_model_name: 'Model',
        config_custom_model_hint: 'Enter custom model name',
        config_save: 'Save', config_saved: 'Saved',
        config_save_error: 'Save failed',
        config_custom_option: 'Custom...',
        config_security: 'Security', config_password: 'Password',
        config_password_hint: 'Leave empty to disable password protection',
        config_password_changed: 'Password updated, please re-login',
        config_password_cleared: 'Password cleared',
        skills_title: 'Skills', skills_desc: 'View, enable, or disable agent skills', skills_hub_btn: 'Skill Hub',
        skills_loading: 'Loading skills...', skills_loading_desc: 'Skills will be displayed here after loading',
        tools_section_title: 'Built-in Tools', tools_loading: 'Loading tools...',
        skills_section_title: 'Skills', skill_enable: 'Enable', skill_disable: 'Disable',
        skill_toggle_error: 'Operation failed, please try again',
        memory_title: 'Memory', memory_desc: 'View agent memory files and contents',
        memory_tab_files: 'Memory Files', memory_tab_dreams: 'Dream Diary',
        memory_loading: 'Loading memory files...', memory_loading_desc: 'Memory files will be displayed here',
        memory_back: 'Back to list',
        memory_col_name: 'Filename', memory_col_type: 'Type', memory_col_size: 'Size', memory_col_updated: 'Updated',
        channels_title: 'Channels', channels_desc: 'Manage connected messaging channels',
        channels_add: 'Connect', channels_disconnect: 'Disconnect',
        channels_save: 'Save', channels_saved: 'Saved', channels_save_error: 'Save failed',
        channels_restarted: 'Saved & Restarted',
        channels_connect_btn: 'Connect', channels_cancel: 'Cancel',
        channels_select_placeholder: 'Select a channel to connect...',
        channels_empty: 'No channels connected', channels_empty_desc: 'Click the "Connect" button above to get started',
        channels_disconnect_confirm: 'Disconnect this channel? Config will be preserved but the channel will stop.',
        channels_connected: 'Connected', channels_connecting: 'Connecting...',
        weixin_scan_title: 'WeChat QR Login', weixin_scan_desc: 'Scan the QR code below with WeChat',
        weixin_scan_loading: 'Loading QR code...', weixin_scan_waiting: 'Waiting for scan...',
        weixin_scan_scanned: 'Scanned, please confirm on your phone', weixin_scan_expired: 'QR code expired, refreshing...',
        weixin_scan_success: 'Login successful, starting channel...', weixin_scan_fail: 'Failed to load QR code',
        weixin_qr_tip: 'QR code expires in ~2 minutes',
        wecom_scan_btn: 'Scan to Create WeCom Bot', wecom_scan_desc: 'Scan with WeCom to create a bot instantly',
        wecom_scan_success: 'Bot created, starting channel...',
        wecom_scan_fail: 'Bot creation failed',
        wecom_mode_scan: 'Scan QR', wecom_mode_manual: 'Manual',
        tasks_title: 'Scheduled Tasks', tasks_desc: 'View and manage scheduled tasks',
        tasks_coming: 'Coming Soon', tasks_coming_desc: 'Scheduled task management will be available here',
        logs_title: 'Logs', logs_desc: 'Real-time log output (run.log)',
        logs_live: 'Live', logs_coming_msg: 'Log streaming will be available here. Connects to run.log for real-time output similar to tail -f.',
        new_chat: 'New Chat',
        session_history: 'History',
        today: 'Today', yesterday: 'Yesterday', earlier: 'Earlier',
        delete_session_confirm: 'Delete this session? All messages will be removed.',
        delete_session_title: 'Delete Session',
        untitled_session: 'New Chat',
        context_cleared: '— Context above has been cleared —',
        tip_new_chat: 'New Chat',
        tip_clear_context: 'Clear Context',
        tip_attach_file: 'Attach File',
        confirm_yes: 'Confirm',
        confirm_cancel: 'Cancel',
        error_send: 'Failed to send. Please try again.', error_timeout: 'Request timeout. Please try again.',
        thinking_in_progress: 'Thinking...', thinking_done: 'Thought', thinking_duration: 'Duration',
        agents_title: 'Agent Management', agents_desc: 'Create, configure and manage Agent instances',
        agents_create: 'Create Agent', agents_edit: 'Edit Agent',
        agents_loading: 'Loading agents...', agents_loading_desc: 'Agent list will be displayed here',
        agents_filter_tenant: 'Tenant Filter', agents_refresh: 'Refresh',
        agents_empty: 'No agents yet', agents_empty_desc: 'Click the "Create Agent" button above to get started',
        agents_section_basic: 'Basic Info', agents_section_tools: 'Tools',
        agents_section_skills: 'Skills', agents_section_knowledge: 'Knowledge',
        agents_section_mcp: 'MCP Server',
        agents_field_tenant: 'Tenant ID', agents_field_id: 'Agent ID', agents_field_name: 'Name',
        agents_field_id_hint: 'Leave empty to auto-generate (recommended)',
        agents_field_model: 'Model', agents_field_prompt: 'System Prompt',
        agents_knowledge_enabled: 'Enable Knowledge',
        agents_loading_tools: 'Loading tools...', agents_loading_skills: 'Loading skills...',
        agents_add_mcp: 'Add Server', agents_mcp_name: 'Name',
        agents_mcp_command: 'Command', agents_mcp_args: 'Args',
        agents_cancel: 'Cancel', agents_save: 'Save',
        agents_delete: 'Delete', agents_delete_confirm: 'Delete this agent? This action cannot be undone.',
        agents_delete_title: 'Delete Agent',
        agents_save_success: 'Saved', agents_save_error: 'Save failed',
        agents_tools_count: 'tools', agents_skills_count: 'skills',
        agents_knowledge_on: 'Knowledge enabled', agents_knowledge_off: 'Knowledge disabled',
        bindings_title: 'Binding Management',
        bindings_desc: 'Manage routing bindings across tenants, channels and agents',
        bindings_create: 'Create Binding',
        bindings_edit: 'Edit Binding',
        bindings_loading: 'Loading bindings...',
        bindings_loading_desc: 'Binding list will be displayed here',
        bindings_empty: 'No bindings yet',
        bindings_empty_desc: 'Click the "Create Binding" button above to get started',
        bindings_section_basic: 'Basic Info',
        bindings_section_route: 'Routing Rules',
        bindings_field_tenant: 'Tenant ID',
        bindings_field_id: 'Binding ID',
        bindings_field_name: 'Name',
        bindings_field_channel: 'Channel Type',
        bindings_field_agent: 'Target Agent',
        bindings_field_enabled: 'Enable Binding',
        bindings_field_app_id: 'External App ID',
        bindings_field_chat_id: 'External Chat ID',
        bindings_field_user_id: 'External User ID',
        bindings_route_hint: 'Leave fields empty for broader matching. More fields make routing more specific.',
        bindings_route_any: 'Matches all messages on this channel',
        bindings_route_prefix: 'Match rules',
        bindings_route_app: 'App',
        bindings_route_chat: 'Chat',
        bindings_route_user: 'User',
        bindings_status_enabled: 'Enabled',
        bindings_status_disabled: 'Disabled',
        bindings_route_disabled: 'This binding is excluded from routing',
        bindings_cancel: 'Cancel',
        bindings_save: 'Save',
        bindings_save_error: 'Save failed',
        bindings_delete: 'Delete',
        bindings_delete_title: 'Delete Binding',
        bindings_delete_confirm: 'Delete this binding? This action cannot be undone.',
        bindings_no_agents: 'No agents available for this tenant',
        bindings_loading_agents: 'Loading agents...',
        tenants_title: 'Tenant Management',
        tenants_desc: 'Create and manage tenant boundaries',
        tenants_create: 'Create Tenant',
        tenants_edit: 'Edit Tenant',
        tenants_loading: 'Loading tenants...',
        tenants_loading_desc: 'Tenant list will be displayed here',
        tenants_empty: 'No tenants yet',
        tenants_empty_desc: 'Click the "Create Tenant" button above to get started',
        tenants_field_id: 'Tenant ID',
        tenants_field_name: 'Name',
        tenants_field_status: 'Status',
        tenants_save: 'Save',
        tenants_cancel: 'Cancel',
        tenants_save_error: 'Save failed',
        tenants_delete_title: 'Delete Tenant',
        tenants_delete_confirm: 'Delete this tenant? This operation is risky.',
        tenant_users_title: 'Tenant Role Management',
        tenant_users_desc: 'Manage users, roles, and statuses under each tenant',
        tenant_users_create: 'Add User',
        tenant_users_edit: 'Edit User',
        tenant_users_loading: 'Loading tenant users...',
        tenant_users_loading_desc: 'Tenant user list will be displayed here',
        tenant_users_empty: 'No tenant users yet',
        tenant_users_empty_desc: 'Click the "Add User" button above to get started',
        tenant_users_filter_tenant: 'Tenant Filter',
        tenant_users_refresh: 'Refresh',
        tenant_users_field_tenant: 'Tenant ID',
        tenant_users_field_user_id: 'User ID',
        tenant_users_field_name: 'Name',
        tenant_users_field_role: 'Role',
        tenant_users_field_status: 'Status',
        tenant_users_save: 'Save',
        tenant_users_cancel: 'Cancel',
        tenant_users_save_error: 'Save failed',
        tenant_users_delete_title: 'Delete Tenant User',
        tenant_users_delete_confirm: 'Delete this tenant user?',
        tenant_users_no_tenants: 'No tenants found, create a tenant first',
        tenant_users_load_meta_error: 'Failed to load role metadata',
        menu_mcp: 'MCP',
        mcp_title: 'MCP Server Management', mcp_desc: 'Manage Model Context Protocol server connections',
        mcp_add_server: 'Add Server', mcp_server_name: 'Server Name',
        mcp_command: 'Command', mcp_args: 'Arguments',
        mcp_env: 'Environment Variables', mcp_add_env: 'Add Variable',
        mcp_test_connection: 'Test Connection', mcp_tools_provided: 'Tools Provided',
        mcp_no_servers: 'No MCP servers configured', mcp_no_servers_desc: 'Click the "Add Server" button above to get started',
        mcp_loading: 'Loading MCP servers...', mcp_loading_desc: 'MCP server list will be displayed here',
        mcp_select_agent: 'Select Agent', mcp_test_success: 'Connection successful', mcp_test_failed: 'Connection failed',
        mcp_test_testing: 'Testing...', mcp_tools_found: '{n} tools found',
        mcp_delete: 'Delete', mcp_delete_confirm: 'Delete this MCP server?', mcp_delete_title: 'Delete MCP Server',
        mcp_save: 'Save', mcp_cancel: 'Cancel',
        mcp_save_success: 'Saved', mcp_save_error: 'Save failed',
        mcp_view_tools: 'View Tools', mcp_hide_tools: 'Hide Tools',
        mcp_env_key: 'Key', mcp_env_value: 'Value',
        mcp_edit: 'Edit', mcp_edit_server: 'Edit Server',
        mcp_no_tools: 'No tools info available', mcp_name_required: 'Server name is required',
        mcp_command_required: 'Command is required',
    }
};

let currentLang = localStorage.getItem('cow_lang') || 'zh';

function t(key) {
    return (I18N[currentLang] && I18N[currentLang][key]) || (I18N.en[key]) || key;
}

function applyI18n() {
    document.querySelectorAll('[data-i18n]').forEach(el => {
        el.textContent = t(el.dataset.i18n);
    });
    document.querySelectorAll('[data-i18n-html]').forEach(el => {
        el.innerHTML = t(el.dataset.i18nHtml);
    });
    document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
        el.placeholder = t(el.dataset['i18nPlaceholder']);
    });
    document.querySelectorAll('[data-tip-key]').forEach(el => {
        el.setAttribute('data-tooltip', t(el.dataset.tipKey));
    });
    const langLabel = document.getElementById('lang-label');
    if (langLabel) langLabel.textContent = currentLang === 'zh' ? '中文' : 'EN';
}

function toggleLanguage() {
    currentLang = currentLang === 'zh' ? 'en' : 'zh';
    localStorage.setItem('cow_lang', currentLang);
    applyI18n();
    _applyInputTooltips();
}

// =====================================================================
// Theme
// =====================================================================
let currentTheme = localStorage.getItem('cow_theme') || 'dark';

function applyTheme() {
    const root = document.documentElement;
    if (currentTheme === 'dark') {
        root.classList.add('dark');
        document.getElementById('theme-icon').className = 'fas fa-sun';
        document.getElementById('hljs-light').disabled = true;
        document.getElementById('hljs-dark').disabled = false;
    } else {
        root.classList.remove('dark');
        document.getElementById('theme-icon').className = 'fas fa-moon';
        document.getElementById('hljs-light').disabled = false;
        document.getElementById('hljs-dark').disabled = true;
    }
}

function toggleTheme() {
    currentTheme = currentTheme === 'dark' ? 'light' : 'dark';
    localStorage.setItem('cow_theme', currentTheme);
    applyTheme();
}

// =====================================================================
// Sidebar & Navigation
// =====================================================================
const VIEW_META = {
    chat:     { group: 'nav_chat',    page: 'menu_chat' },
    config:   { group: 'nav_manage',  page: 'menu_config' },
    skills:   { group: 'nav_manage',  page: 'menu_skills' },
    agents:   { group: 'nav_manage',  page: 'menu_agents' },
    bindings: { group: 'nav_manage',  page: 'menu_bindings' },
    tenants:  { group: 'nav_manage',  page: 'menu_tenants' },
    tenant_users: { group: 'nav_manage', page: 'menu_tenant_users' },
    mcp:      { group: 'nav_manage',  page: 'menu_mcp' },
    memory:   { group: 'nav_manage',  page: 'menu_memory' },
    knowledge:{ group: 'nav_manage',  page: 'menu_knowledge' },
    channels: { group: 'nav_manage',  page: 'menu_channels' },
    tasks:    { group: 'nav_manage',  page: 'menu_tasks' },
    logs:     { group: 'nav_monitor', page: 'menu_logs' },
};

let currentView = 'chat';

function navigateTo(viewId) {
    if (!VIEW_META[viewId]) return;
    document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
    const target = document.getElementById('view-' + viewId);
    if (target) target.classList.add('active');
    document.querySelectorAll('.sidebar-item').forEach(item => {
        item.classList.toggle('active', item.dataset.view === viewId);
    });
    const meta = VIEW_META[viewId];
    document.getElementById('breadcrumb-group').textContent = t(meta.group);
    document.getElementById('breadcrumb-group').dataset.i18n = meta.group;
    document.getElementById('breadcrumb-page').textContent = t(meta.page);
    document.getElementById('breadcrumb-page').dataset.i18n = meta.page;
    currentView = viewId;
    if (window.innerWidth < 1024) closeSidebar();
}

function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebar-overlay');
    const isOpen = !sidebar.classList.contains('-translate-x-full');
    if (isOpen) {
        closeSidebar();
    } else {
        sidebar.classList.remove('-translate-x-full');
        overlay.classList.remove('hidden');
    }
}

function closeSidebar() {
    document.getElementById('sidebar').classList.add('-translate-x-full');
    document.getElementById('sidebar-overlay').classList.add('hidden');
}

document.querySelectorAll('.menu-group > button').forEach(btn => {
    btn.addEventListener('click', () => {
        btn.parentElement.classList.toggle('open');
    });
});

document.querySelectorAll('.sidebar-item').forEach(item => {
    item.addEventListener('click', () => navigateTo(item.dataset.view));
});

window.addEventListener('resize', () => {
    if (window.innerWidth >= 1024) {
        document.getElementById('sidebar').classList.remove('-translate-x-full');
        document.getElementById('sidebar-overlay').classList.add('hidden');
    } else {
        if (!document.getElementById('sidebar').classList.contains('-translate-x-full')) {
            closeSidebar();
        }
    }
});

// =====================================================================
// Markdown Renderer
// =====================================================================
function createMd() {
    const md = window.markdownit({
        html: false, breaks: true, linkify: true, typographer: true,
        highlight: function(str, lang) {
            if (lang && hljs.getLanguage(lang)) {
                try { return hljs.highlight(str, { language: lang }).value; } catch (_) {}
            }
            return hljs.highlightAuto(str).value;
        }
    });
    const defaultLinkOpen = md.renderer.rules.link_open || function(tokens, idx, options, env, self) {
        return self.renderToken(tokens, idx, options);
    };
    md.renderer.rules.link_open = function(tokens, idx, options, env, self) {
        tokens[idx].attrPush(['target', '_blank']);
        tokens[idx].attrPush(['rel', 'noopener noreferrer']);
        return defaultLinkOpen(tokens, idx, options, env, self);
    };
    return md;
}

const md = createMd();

const VIDEO_EXT_RE = /\.(?:mp4|webm|mov|avi|mkv)$/i;  // tested against URL without query string

function _buildVideoHtml(url) {
    const fileName = url.split('/').pop().split('?')[0];
    return `<div style="margin:10px 0;">` +
        `<video controls preload="metadata" ` +
        `style="max-width:100%;border-radius:10px;box-shadow:0 2px 8px rgba(0,0,0,0.15);display:block;">` +
        `<source src="${url}"></video>` +
        `<a href="${url}" target="_blank" ` +
        `style="display:inline-flex;align-items:center;gap:4px;margin-top:4px;font-size:12px;color:#8b8fa8;text-decoration:none;">` +
        `<i class="fas fa-download"></i> ${escapeHtml(fileName)}</a></div>`;
}

function injectVideoPlayers(html) {
    // Step 1: replace markdown-it anchor tags whose href points to a video file.
    const step1 = html.replace(
        /<a\s+href="(https?:\/\/[^"]+)"[^>]*>[^<]*<\/a>/gi,
        (match, url) => VIDEO_EXT_RE.test(url.split('?')[0]) ? _buildVideoHtml(url) : match
    );
    // Step 2: replace any remaining bare video URLs in text nodes (not inside HTML tags).
    // Split on HTML tags to avoid touching src/href attributes already in markup.
    return step1.split(/(<[^>]+>)/).map((chunk, idx) => {
        // Even indices are text nodes; odd indices are HTML tags — leave them untouched.
        if (idx % 2 !== 0) return chunk;
        return chunk.replace(/https?:\/\/\S+/gi, (url) => {
            const bare = url.replace(/[),.\s]+$/, '');  // strip trailing punctuation
            return VIDEO_EXT_RE.test(bare.split('?')[0]) ? _buildVideoHtml(bare) : url;
        });
    }).join('');
}

function renderMarkdown(text) {
    try {
        const html = md.render(text);
        return injectVideoPlayers(html);
    }
    catch (e) { return text.replace(/\n/g, '<br>'); }
}

// =====================================================================
// Chat Module
// =====================================================================
let isPolling = false;
let pollGeneration = 0;   // incremented on each restart to cancel stale poll loops
let loadingContainers = {};
let activeStreams = {};   // request_id -> EventSource
let isComposing = false;
let appConfig = { use_agent: false, title: 'CowAgent', subtitle: '', providers: {}, api_bases: {} };

const SESSION_ID_KEY = 'cow_session_id';
const AGENT_ID_KEY = 'cow_agent_id';
const BINDING_ID_KEY = 'cow_binding_id';

function generateSessionId() {
    return 'session_' + ([1e7]+-1e3+-4e3+-8e3+-1e11).replace(/[018]/g, c =>
        (c ^ crypto.getRandomValues(new Uint8Array(1))[0] & 15 >> c / 4).toString(16)
    );
}

// Restore session_id from localStorage so conversation history survives page refresh.
// A new id is only generated when the user explicitly starts a new chat.
function loadOrCreateSessionId() {
    const stored = localStorage.getItem(SESSION_ID_KEY);
    if (stored) return stored;
    const fresh = generateSessionId();
    localStorage.setItem(SESSION_ID_KEY, fresh);
    return fresh;
}

let sessionId = loadOrCreateSessionId();
let currentAgentId = localStorage.getItem(AGENT_ID_KEY) || '';
let currentBindingId = localStorage.getItem(BINDING_ID_KEY) || '';

// ---- Conversation history state ----
let historyPage = 0;       // last page fetched (0 = nothing fetched yet)
let historyHasMore = false;
let historyLoading = false;

fetch('/config').then(r => r.json()).then(data => {
    if (data.status === 'success') {
        appConfig = data;
        const title = data.title || 'CowAgent';
        document.getElementById('welcome-title').textContent = title;
        initConfigView(data);
    }
    loadBindingList();
    loadAgentList();
    loadHistory(1);
}).catch(() => { loadBindingList(); loadAgentList(); loadHistory(1); });

// Start polling immediately so scheduler/push messages are received at any time
startPolling();

const chatInput = document.getElementById('chat-input');
const sendBtn = document.getElementById('send-btn');
const messagesDiv = document.getElementById('chat-messages');
const fileInput = document.getElementById('file-input');
const agentSelect = document.getElementById('agent-select');
const bindingSelect = document.getElementById('binding-select');

function appendAgentQuery(url) {
    if (currentBindingId) {
        const sep = url.includes('?') ? '&' : '?';
        return `${url}${sep}binding_id=${encodeURIComponent(currentBindingId)}`;
    }
    if (!currentAgentId) return url;
    const sep = url.includes('?') ? '&' : '?';
    return `${url}${sep}agent_id=${encodeURIComponent(currentAgentId)}`;
}

function withAgentBody(body) {
    if (currentBindingId) {
        body.binding_id = currentBindingId;
        return body;
    }
    if (currentAgentId) body.agent_id = currentAgentId;
    return body;
}

function resetRuntimeScopedViews() {
    historyPage = 0;
    historyHasMore = false;
    historyLoading = false;
    messagesDiv.innerHTML = '';
    loadHistory(1);
    loadSessionList();
    startPolling();
}

function loadBindingList() {
    if (!bindingSelect) return;
    fetch('/api/bindings?channel_type=web')
        .then(r => r.json())
        .then(data => {
            if (data.status !== 'success') return;
            const bindings = data.bindings || [];
            const options = ['<option value="">渠道绑定</option>'];
            bindings.forEach(binding => {
                const selected = binding.binding_id === currentBindingId ? ' selected' : '';
                const tenantText = binding.tenant_id || 'default';
                const agentText = binding.agent_id || '';
                const label = `${binding.name || binding.binding_id} (${tenantText}/${agentText})`;
                options.push(
                    `<option value="${escapeHtml(binding.binding_id)}"${selected}>${escapeHtml(label)}</option>`
                );
            });
            bindingSelect.innerHTML = options.join('');

            if (currentBindingId && !bindings.some(binding => binding.binding_id === currentBindingId)) {
                currentBindingId = '';
                localStorage.removeItem(BINDING_ID_KEY);
                bindingSelect.value = '';
            }
        })
        .catch(() => {});
}

function loadAgentList() {
    if (!agentSelect) return;
    fetch('/api/agents')
        .then(r => r.json())
        .then(data => {
            if (data.status !== 'success') return;
            const agents = data.agents || [];
            const options = ['<option value="">当前工作区</option>'];
            agents.forEach(agent => {
                const selected = agent.agent_id === currentAgentId ? ' selected' : '';
                options.push(
                    `<option value="${escapeHtml(agent.agent_id)}"${selected}>${escapeHtml(agent.name || agent.agent_id)}</option>`
                );
            });
            agentSelect.innerHTML = options.join('');

            if (currentAgentId && !agents.some(agent => agent.agent_id === currentAgentId)) {
                currentAgentId = '';
                localStorage.removeItem(AGENT_ID_KEY);
                agentSelect.value = '';
            }
        })
        .catch(() => {});
}

if (agentSelect) {
    agentSelect.addEventListener('change', () => {
        currentAgentId = agentSelect.value || '';
        if (currentAgentId) {
            localStorage.setItem(AGENT_ID_KEY, currentAgentId);
            currentBindingId = '';
            localStorage.removeItem(BINDING_ID_KEY);
            if (bindingSelect) bindingSelect.value = '';
        } else {
            localStorage.removeItem(AGENT_ID_KEY);
        }
        resetRuntimeScopedViews();
    });
}

if (bindingSelect) {
    bindingSelect.addEventListener('change', () => {
        currentBindingId = bindingSelect.value || '';
        if (currentBindingId) {
            localStorage.setItem(BINDING_ID_KEY, currentBindingId);
            currentAgentId = '';
            localStorage.removeItem(AGENT_ID_KEY);
            if (agentSelect) agentSelect.value = '';
        } else {
            localStorage.removeItem(BINDING_ID_KEY);
        }
        resetRuntimeScopedViews();
    });
}

// Intercept internal navigation links in chat messages
messagesDiv.addEventListener('click', (e) => {
    const copyBtn = e.target.closest('.copy-msg-btn');
    if (copyBtn) {
        e.preventDefault();
        const msgRoot = copyBtn.closest('.flex.gap-3');
        const answerEl = msgRoot && msgRoot.querySelector('.answer-content');
        const rawMd = answerEl && answerEl.dataset.rawMd;
        if (rawMd) {
            navigator.clipboard.writeText(rawMd).then(() => {
                const icon = copyBtn.querySelector('i');
                if (icon) { icon.className = 'fas fa-check'; setTimeout(() => { icon.className = 'fas fa-copy'; }, 1500); }
            });
        }
        return;
    }
    const a = e.target.closest('a');
    if (!a) return;
    const href = a.getAttribute('href') || '';
    if (href === '/memory/dreams') {
        e.preventDefault();
        navigateTo('memory');
        setTimeout(() => switchMemoryTab('dreams'), 50);
    } else if (href === '/memory/MEMORY.md') {
        e.preventDefault();
        navigateTo('memory');
        setTimeout(() => { switchMemoryTab('files'); openMemoryFile('MEMORY.md', 'memory'); }, 50);
    }
});
const attachmentPreview = document.getElementById('attachment-preview');

// Pending attachments: [{file_path, file_name, file_type, preview_url}]
// Items with _uploading=true are still in flight.
let pendingAttachments = [];
let uploadingCount = 0;

// Input history (like terminal arrow-key recall)
const inputHistory = [];
let historyIdx = -1;
let historySavedDraft = '';

function updateSendBtnState() {
    sendBtn.disabled = uploadingCount > 0 || (!chatInput.value.trim() && pendingAttachments.length === 0);
}

function renderAttachmentPreview() {
    if (pendingAttachments.length === 0) {
        attachmentPreview.classList.add('hidden');
        attachmentPreview.innerHTML = '';
        updateSendBtnState();
        return;
    }
    attachmentPreview.classList.remove('hidden');
    attachmentPreview.innerHTML = pendingAttachments.map((att, idx) => {
        if (att._uploading) {
            return `<div class="att-chip att-uploading" data-idx="${idx}">
                <i class="fas fa-spinner fa-spin"></i>
                <span class="att-name">${escapeHtml(att.file_name)}</span>
            </div>`;
        }
        if (att.file_type === 'image') {
            return `<div class="att-thumb" data-idx="${idx}">
                <img src="${att.preview_url}" alt="${escapeHtml(att.file_name)}">
                <button class="att-remove" onclick="removeAttachment(${idx})">&times;</button>
            </div>`;
        }
        const icon = att.file_type === 'video' ? 'fa-film' : 'fa-file-alt';
        return `<div class="att-chip" data-idx="${idx}">
            <i class="fas ${icon}"></i>
            <span class="att-name">${escapeHtml(att.file_name)}</span>
            <button class="att-remove" onclick="removeAttachment(${idx})">&times;</button>
        </div>`;
    }).join('');
    updateSendBtnState();
}

function removeAttachment(idx) {
    if (pendingAttachments[idx]?._uploading) return;
    pendingAttachments.splice(idx, 1);
    renderAttachmentPreview();
}

async function handleFileSelect(files) {
    if (!files || files.length === 0) return;
    const tasks = [];
    for (const file of files) {
        const placeholder = { file_name: file.name, file_type: 'file', _uploading: true };
        pendingAttachments.push(placeholder);
        uploadingCount++;
        renderAttachmentPreview();

        tasks.push((async () => {
            const formData = new FormData();
            formData.append('file', file);
            formData.append('session_id', sessionId);
            if (currentBindingId) {
                formData.append('binding_id', currentBindingId);
            } else if (currentAgentId) {
                formData.append('agent_id', currentAgentId);
            }
            try {
                const resp = await fetch('/upload', { method: 'POST', body: formData });
                const data = await resp.json();
                if (data.status === 'success') {
                    placeholder.file_path = data.file_path;
                    placeholder.file_name = data.file_name;
                    placeholder.file_type = data.file_type;
                    placeholder.preview_url = data.preview_url;
                    delete placeholder._uploading;
                } else {
                    const i = pendingAttachments.indexOf(placeholder);
                    if (i !== -1) pendingAttachments.splice(i, 1);
                }
            } catch (e) {
                console.error('Upload failed:', e);
                const i = pendingAttachments.indexOf(placeholder);
                if (i !== -1) pendingAttachments.splice(i, 1);
            }
            uploadingCount--;
            renderAttachmentPreview();
        })());
    }
    await Promise.all(tasks);
}

fileInput.addEventListener('change', function() {
    handleFileSelect(this.files);
    this.value = '';
});

// Drag-and-drop support on chat input area
const chatInputArea = chatInput.closest('.flex-shrink-0');
chatInputArea.addEventListener('dragover', (e) => { e.preventDefault(); e.stopPropagation(); chatInputArea.classList.add('drag-over'); });
chatInputArea.addEventListener('dragleave', (e) => { e.preventDefault(); e.stopPropagation(); chatInputArea.classList.remove('drag-over'); });
chatInputArea.addEventListener('drop', (e) => {
    e.preventDefault(); e.stopPropagation();
    chatInputArea.classList.remove('drag-over');
    if (e.dataTransfer.files.length) handleFileSelect(e.dataTransfer.files);
});

// Paste image support
chatInput.addEventListener('paste', (e) => {
    const items = e.clipboardData?.items;
    if (!items) return;
    const files = [];
    for (const item of items) {
        if (item.kind === 'file') {
            files.push(item.getAsFile());
        }
    }
    if (files.length) {
        e.preventDefault();
        handleFileSelect(files);
    }
});

chatInput.addEventListener('compositionstart', () => { isComposing = true; });
chatInput.addEventListener('compositionend', () => { setTimeout(() => { isComposing = false; }, 100); });

// ── Slash Command Menu ───────────────────────────────────────
const SLASH_COMMANDS = [
    { cmd: '/help',                desc: '显示命令帮助' },
    { cmd: '/status',              desc: '查看运行状态' },
    { cmd: '/context',             desc: '查看对话上下文' },
    { cmd: '/context clear',       desc: '清除对话上下文' },
    { cmd: '/skill list',          desc: '查看已安装技能' },
    { cmd: '/skill list --remote', desc: '浏览技能广场' },
    { cmd: '/skill search ',       desc: '搜索技能' },
    { cmd: '/skill install ',      desc: '安装技能 (名称或 GitHub URL)' },
    { cmd: '/skill uninstall ',    desc: '卸载技能' },
    { cmd: '/skill info ',         desc: '查看技能详情' },
    { cmd: '/skill enable ',       desc: '启用技能' },
    { cmd: '/skill disable ',      desc: '禁用技能' },
    { cmd: '/memory dream ',        desc: '手动触发记忆蒸馏 (可指定天数, 默认3)' },
    { cmd: '/knowledge',            desc: '查看知识库统计' },
    { cmd: '/knowledge list',      desc: '查看知识库文件树' },
    { cmd: '/knowledge on',        desc: '开启知识库' },
    { cmd: '/knowledge off',       desc: '关闭知识库' },
    { cmd: '/config',              desc: '查看当前配置' },
    { cmd: '/logs',                desc: '查看最近日志' },
    { cmd: '/version',             desc: '查看版本' },
];

const slashMenu = document.getElementById('slash-menu');
let slashActiveIdx = 0;
let slashFiltered = [];
let slashJustSelected = false;
let slashLastFilter = '';
let slashLastMouseX = -1;
let slashLastMouseY = -1;

function showSlashMenu(filter) {
    const q = filter.toLowerCase();
    if (q === slashLastFilter && !slashMenu.classList.contains('hidden')) return;
    slashLastFilter = q;

    const newFiltered = SLASH_COMMANDS.filter(c => c.cmd.toLowerCase().startsWith(q));
    if (newFiltered.length === 0) {
        hideSlashMenu();
        return;
    }

    const changed = newFiltered.length !== slashFiltered.length ||
        newFiltered.some((c, i) => c.cmd !== slashFiltered[i]?.cmd);
    slashFiltered = newFiltered;
    if (changed) slashActiveIdx = 0;
    slashActiveIdx = Math.min(slashActiveIdx, slashFiltered.length - 1);

    slashNavByKeyboard = true;
    renderSlashItems();
    slashMenu.classList.remove('hidden');
}

function hideSlashMenu() {
    slashMenu.classList.add('hidden');
    slashMenu.innerHTML = '';
    slashFiltered = [];
    slashActiveIdx = -1;
    slashLastFilter = '';
    slashNavByKeyboard = false;
    slashLastMouseX = -1;
    slashLastMouseY = -1;
}

function isSlashMenuVisible() {
    return !slashMenu.classList.contains('hidden') && slashFiltered.length > 0;
}

function renderSlashItems() {
    slashMenu.innerHTML =
        '<div class="slash-menu-header">Commands</div>' +
        slashFiltered.map((c, i) =>
            `<div class="slash-menu-item${i === slashActiveIdx ? ' active' : ''}" data-idx="${i}">` +
            `<span class="cmd">${escapeHtml(c.cmd)}</span>` +
            `<span class="desc">${escapeHtml(c.desc)}</span></div>`
        ).join('');

    const activeEl = slashMenu.querySelector('.slash-menu-item.active');
    if (activeEl) activeEl.scrollIntoView({ block: 'nearest' });
}

// Delegated events on the persistent slashMenu container (not destroyed by innerHTML)
// Use coordinate comparison to distinguish real mouse movement from DOM-rebuild phantom events.
slashMenu.addEventListener('mousemove', (e) => {
    if (e.clientX === slashLastMouseX && e.clientY === slashLastMouseY) return;
    slashLastMouseX = e.clientX;
    slashLastMouseY = e.clientY;
    if (!slashNavByKeyboard) return;
    slashNavByKeyboard = false;
    const item = e.target.closest('.slash-menu-item');
    if (!item) return;
    const idx = parseInt(item.dataset.idx);
    if (idx === slashActiveIdx) return;
    slashActiveIdx = idx;
    slashMenu.querySelectorAll('.slash-menu-item').forEach(el => {
        el.classList.toggle('active', parseInt(el.dataset.idx) === idx);
    });
});

slashMenu.addEventListener('mouseover', (e) => {
    if (slashNavByKeyboard) return;
    const item = e.target.closest('.slash-menu-item');
    if (!item) return;
    const idx = parseInt(item.dataset.idx);
    if (idx === slashActiveIdx) return;
    slashActiveIdx = idx;
    slashMenu.querySelectorAll('.slash-menu-item').forEach(el => {
        el.classList.toggle('active', parseInt(el.dataset.idx) === idx);
    });
});

slashMenu.addEventListener('mousedown', (e) => {
    const item = e.target.closest('.slash-menu-item');
    if (!item) return;
    e.preventDefault();
    selectSlashCommand(parseInt(item.dataset.idx));
});

function selectSlashCommand(idx) {
    if (idx < 0 || idx >= slashFiltered.length) return;
    const chosen = slashFiltered[idx].cmd;
    slashJustSelected = true;
    chatInput.value = chosen;
    chatInput.dispatchEvent(new Event('input'));
    hideSlashMenu();
    chatInput.focus();
    chatInput.selectionStart = chatInput.selectionEnd = chosen.length;
}

chatInput.addEventListener('input', function() {
    this.style.height = '42px';
    const scrollH = this.scrollHeight;
    const newH = Math.min(scrollH, 180);
    this.style.height = newH + 'px';
    this.style.overflowY = scrollH > 180 ? 'auto' : 'hidden';
    updateSendBtnState();

    const val = this.value;
    if (slashJustSelected) {
        slashJustSelected = false;
    } else if (val.startsWith('/')) {
        showSlashMenu(val);
    } else {
        hideSlashMenu();
    }
});

chatInput.addEventListener('keydown', function(e) {
    if (e.keyCode === 229 || e.isComposing || isComposing) return;

    if (isSlashMenuVisible()) {
        if (e.key === 'ArrowDown') {
            e.preventDefault();
            slashNavByKeyboard = true;
            slashActiveIdx = Math.min(slashActiveIdx + 1, slashFiltered.length - 1);
            renderSlashItems();
            return;
        }
        if (e.key === 'ArrowUp') {
            e.preventDefault();
            slashNavByKeyboard = true;
            slashActiveIdx = Math.max(slashActiveIdx - 1, 0);
            renderSlashItems();
            return;
        }
        if (e.key === 'Enter' && !e.shiftKey && !e.ctrlKey) {
            e.preventDefault();
            selectSlashCommand(slashActiveIdx);
            return;
        }
        if (e.key === 'Escape') {
            e.preventDefault();
            hideSlashMenu();
            return;
        }
        if (e.key === 'Tab') {
            e.preventDefault();
            selectSlashCommand(slashActiveIdx);
            return;
        }
    }

    // Arrow-key history recall (only when input is empty or already browsing history)
    if (e.key === 'ArrowUp' && inputHistory.length > 0 && !isSlashMenuVisible()) {
        const curVal = this.value.trim();
        const isSingleLine = !this.value.includes('\n');
        if (isSingleLine && (curVal === '' || historyIdx >= 0)) {
            e.preventDefault();
            if (historyIdx < 0) {
                historySavedDraft = this.value;
                historyIdx = inputHistory.length - 1;
            } else if (historyIdx > 0) {
                historyIdx--;
            }
            this.value = inputHistory[historyIdx];
            slashJustSelected = true;
            this.dispatchEvent(new Event('input'));
            hideSlashMenu();
            this.selectionStart = this.selectionEnd = this.value.length;
            return;
        }
    }
    if (e.key === 'ArrowDown' && historyIdx >= 0 && !isSlashMenuVisible()) {
        const isSingleLine = !this.value.includes('\n');
        if (isSingleLine) {
            e.preventDefault();
            if (historyIdx < inputHistory.length - 1) {
                historyIdx++;
                this.value = inputHistory[historyIdx];
            } else {
                historyIdx = -1;
                this.value = historySavedDraft;
                historySavedDraft = '';
            }
            slashJustSelected = true;
            this.dispatchEvent(new Event('input'));
            hideSlashMenu();
            this.selectionStart = this.selectionEnd = this.value.length;
            return;
        }
    }

    if ((e.ctrlKey || e.shiftKey) && e.key === 'Enter') {
        const start = this.selectionStart;
        const end = this.selectionEnd;
        this.value = this.value.substring(0, start) + '\n' + this.value.substring(end);
        this.selectionStart = this.selectionEnd = start + 1;
        this.dispatchEvent(new Event('input'));
        e.preventDefault();
    } else if (e.key === 'Enter' && !e.shiftKey && !e.ctrlKey) {
        sendMessage();
        e.preventDefault();
    }
});

chatInput.addEventListener('blur', () => {
    setTimeout(hideSlashMenu, 150);
});

document.querySelectorAll('.example-card').forEach(card => {
    card.addEventListener('click', () => {
        // data-send overrides the visible text (e.g. show "查看全部命令" but send "/help")
        const sendText = card.dataset.send;
        if (sendText) {
            chatInput.value = sendText;
            chatInput.dispatchEvent(new Event('input'));
            chatInput.focus();
            return;
        }
        const textEl = card.querySelector('[data-i18n*="text"]');
        if (textEl) {
            chatInput.value = textEl.textContent;
            chatInput.dispatchEvent(new Event('input'));
            chatInput.focus();
        }
    });
});

function sendMessage() {
    const text = chatInput.value.trim();
    if (!text && pendingAttachments.length === 0) return;

    if (text) {
        inputHistory.push(text);
        historyIdx = -1;
        historySavedDraft = '';
    }

    const ws = document.getElementById('welcome-screen');
    const isFirstMessage = !!ws;
    if (ws) ws.remove();

    const titleInfo = (isFirstMessage && text) ? { sid: sessionId, userMsg: text } : null;

    const timestamp = new Date();
    const attachments = [...pendingAttachments];
    addUserMessage(text, timestamp, attachments);

    const loadingEl = addLoadingIndicator();

    chatInput.value = '';
    chatInput.style.height = '42px';
    chatInput.style.overflowY = 'hidden';
    pendingAttachments = [];
    renderAttachmentPreview();
    sendBtn.disabled = true;

    const body = withAgentBody({ session_id: sessionId, message: text, stream: true, timestamp: timestamp.toISOString() });
    if (attachments.length > 0) {
        body.attachments = attachments.map(a => ({
            file_path: a.file_path,
            file_name: a.file_name,
            file_type: a.file_type,
        }));
    }

    const MAX_RETRIES = 2;
    const RETRY_DELAY_MS = 1000;

    function postWithRetry(attempt) {
        fetch('/message', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        })
        .then(r => r.json())
        .then(data => {
            if (data.status === 'success') {
                if (data.stream) {
                    startSSE(data.request_id, loadingEl, timestamp, titleInfo);
                } else {
                    loadingContainers[data.request_id] = loadingEl;
                }
            } else {
                loadingEl.remove();
                addBotMessage(t('error_send'), new Date());
            }
        })
        .catch(err => {
            if (err.name === 'AbortError') {
                loadingEl.remove();
                addBotMessage(t('error_timeout'), new Date());
                return;
            }
            if (attempt < MAX_RETRIES) {
                console.warn(`[sendMessage] attempt ${attempt + 1} failed, retrying...`, err);
                setTimeout(() => postWithRetry(attempt + 1), RETRY_DELAY_MS * (attempt + 1));
                return;
            }
            loadingEl.remove();
            addBotMessage(t('error_send'), new Date());
        });
    }

    postWithRetry(0);
}

function startSSE(requestId, loadingEl, timestamp, titleInfo) {
    let botEl = null;
    let stepsEl = null;    // .agent-steps  (thinking summaries + tool indicators)
    let contentEl = null;  // .answer-content (final streaming answer)
    let mediaEl = null;    // .media-content (images & file attachments)
    let accumulatedText = '';
    let currentToolEl = null;
    let currentReasoningEl = null;  // live reasoning bubble
    let reasoningText = '';
    let reasoningStartTime = 0;
    let done = false;

    const MAX_RECONNECTS = 10;
    const RECONNECT_BASE_MS = 1000;
    let reconnectCount = 0;

    function ensureBotEl() {
        if (botEl) return;
        if (loadingEl) { loadingEl.remove(); loadingEl = null; }
        botEl = document.createElement('div');
        botEl.className = 'flex gap-3 px-4 sm:px-6 py-3';
        botEl.dataset.requestId = requestId;
        botEl.innerHTML = `
            <img src="assets/logo.jpg" alt="CowAgent" class="w-8 h-8 rounded-lg flex-shrink-0">
            <div class="min-w-0 flex-1 max-w-[85%]">
                <div class="bg-white dark:bg-[#1A1A1A] border border-slate-200 dark:border-white/10 rounded-2xl px-4 py-3 text-sm leading-relaxed msg-content text-slate-700 dark:text-slate-200">
                    <div class="agent-steps"></div>
                    <div class="answer-content sse-streaming"></div>
                    <div class="media-content"></div>
                </div>
                <div class="flex items-center gap-2 mt-1.5">
                    <span class="text-xs text-slate-400 dark:text-slate-500">${formatTime(timestamp)}</span>
                    <button class="copy-msg-btn text-xs text-slate-300 dark:text-slate-600 hover:text-slate-500 dark:hover:text-slate-400 transition-colors cursor-pointer" title="${currentLang === 'zh' ? '复制' : 'Copy'}" style="display:none">
                        <i class="fas fa-copy"></i>
                    </button>
                </div>
            </div>
        `;
        messagesDiv.appendChild(botEl);
        stepsEl = botEl.querySelector('.agent-steps');
        contentEl = botEl.querySelector('.answer-content');
        mediaEl = botEl.querySelector('.media-content');
    }

    function connect() {
        const es = new EventSource(`/stream?request_id=${encodeURIComponent(requestId)}`);
        activeStreams[requestId] = es;

        es.onmessage = function(e) {
            let item;
            try { item = JSON.parse(e.data); } catch (_) { return; }

            // Successful data received, reset reconnect counter
            reconnectCount = 0;

            if (item.type === 'reasoning') {
                ensureBotEl();
                reasoningText += item.content;
                if (!currentReasoningEl) {
                    reasoningStartTime = Date.now();
                    currentReasoningEl = document.createElement('div');
                    currentReasoningEl.className = 'agent-step agent-thinking-step';
                    currentReasoningEl.innerHTML = `
                        <div class="thinking-header" onclick="this.parentElement.classList.toggle('expanded')">
                            <i class="fas fa-lightbulb text-amber-400 flex-shrink-0"></i>
                            <span class="thinking-summary">${t('thinking_in_progress')}</span>
                            <i class="fas fa-chevron-right thinking-chevron"></i>
                        </div>
                        <div class="thinking-full"></div>`;
                    stepsEl.appendChild(currentReasoningEl);
                }
                currentReasoningEl.querySelector('.thinking-full').innerHTML = renderMarkdown(reasoningText);
                scrollChatToBottom();

            } else if (item.type === 'delta') {
                ensureBotEl();
                if (currentReasoningEl) {
                    finalizeThinking(currentReasoningEl, reasoningStartTime, reasoningText);
                    currentReasoningEl = null;
                    reasoningText = '';
                }
                accumulatedText += item.content;
                contentEl.innerHTML = renderMarkdown(accumulatedText);
                scrollChatToBottom();

            } else if (item.type === 'message_end') {
                if (item.has_tool_calls && accumulatedText.trim()) {
                    ensureBotEl();
                    const frozenEl = document.createElement('div');
                    frozenEl.className = 'agent-step agent-content-step';
                    frozenEl.innerHTML = `<div class="agent-content-body">${renderMarkdown(accumulatedText.trim())}</div>`;
                    stepsEl.appendChild(frozenEl);
                    accumulatedText = '';
                    contentEl.innerHTML = '';
                    scrollChatToBottom();
                }

            } else if (item.type === 'tool_start') {
                ensureBotEl();
                if (currentReasoningEl) {
                    finalizeThinking(currentReasoningEl, reasoningStartTime, reasoningText);
                    currentReasoningEl = null;
                    reasoningText = '';
                }
                accumulatedText = '';
                contentEl.innerHTML = '';

                // Add tool execution indicator (collapsible)
                currentToolEl = document.createElement('div');
                currentToolEl.className = 'agent-step agent-tool-step';
                const argsStr = formatToolArgs(item.arguments || {});
                currentToolEl.innerHTML = `
                    <div class="tool-header" onclick="this.parentElement.classList.toggle('expanded')">
                        <i class="fas fa-cog fa-spin text-primary-400 flex-shrink-0 tool-icon"></i>
                        <span class="tool-name">${item.tool}</span>
                        <i class="fas fa-chevron-right tool-chevron"></i>
                    </div>
                    <div class="tool-detail">
                        <div class="tool-detail-section">
                            <div class="tool-detail-label">Input</div>
                            <pre class="tool-detail-content">${argsStr}</pre>
                        </div>
                        <div class="tool-detail-section tool-output-section"></div>
                    </div>`;
                stepsEl.appendChild(currentToolEl);

                scrollChatToBottom();

            } else if (item.type === 'tool_end') {
                if (currentToolEl) {
                    const isError = item.status !== 'success';
                    const icon = currentToolEl.querySelector('.tool-icon');
                    icon.className = isError
                        ? 'fas fa-times text-red-400 flex-shrink-0 tool-icon'
                        : 'fas fa-check text-primary-400 flex-shrink-0 tool-icon';

                    // Show execution time
                    const nameEl = currentToolEl.querySelector('.tool-name');
                    if (item.execution_time !== undefined) {
                        nameEl.innerHTML += ` <span class="tool-time">${item.execution_time}s</span>`;
                    }

                    // Fill output section
                    const outputSection = currentToolEl.querySelector('.tool-output-section');
                    if (outputSection && item.result) {
                        outputSection.innerHTML = `
                            <div class="tool-detail-label">${isError ? 'Error' : 'Output'}</div>
                            <pre class="tool-detail-content ${isError ? 'tool-error-text' : ''}">${escapeHtml(String(item.result))}</pre>`;
                    }

                    if (isError) currentToolEl.classList.add('tool-failed');
                    currentToolEl = null;
                }

            } else if (item.type === 'image') {
                ensureBotEl();
                const imgEl = document.createElement('img');
                imgEl.src = item.content;
                imgEl.alt = 'screenshot';
                imgEl.style.cssText = 'max-width:600px;border-radius:8px;margin:8px 0;cursor:pointer;box-shadow:0 1px 4px rgba(0,0,0,0.1);';
                imgEl.onclick = () => window.open(item.content, '_blank');
                mediaEl.appendChild(imgEl);
                scrollChatToBottom();

            } else if (item.type === 'text') {
                // Intermediate text sent before media items; display it but keep SSE open.
                ensureBotEl();
                contentEl.classList.remove('sse-streaming');
                const textContent = item.content || accumulatedText;
                if (textContent) contentEl.innerHTML = renderMarkdown(textContent);
                applyHighlighting(botEl);
                scrollChatToBottom();

            } else if (item.type === 'video') {
                ensureBotEl();
                const wrapper = document.createElement('div');
                wrapper.innerHTML = _buildVideoHtml(item.content);
                mediaEl.appendChild(wrapper.firstElementChild || wrapper);
                scrollChatToBottom();

            } else if (item.type === 'file') {
                ensureBotEl();
                const fileName = item.file_name || item.content.split('/').pop();
                const fileEl = document.createElement('a');
                fileEl.href = item.content;
                fileEl.download = fileName;
                fileEl.target = '_blank';
                fileEl.className = 'file-attachment';
                fileEl.style.cssText = 'display:inline-flex;align-items:center;gap:6px;padding:8px 14px;margin:8px 0;border-radius:8px;background:var(--bg-secondary,#f3f4f6);color:var(--text-primary,#374151);text-decoration:none;font-size:14px;border:1px solid var(--border-color,#e5e7eb);';
                fileEl.innerHTML = `<i class="fas fa-file-download" style="color:#6b7280;"></i> ${fileName}`;
                mediaEl.appendChild(fileEl);
                scrollChatToBottom();

            } else if (item.type === 'phase') {
                // Coarse progress (e.g. cow install-browser); must not close SSE (unlike "done")
                ensureBotEl();
                const wrap = document.createElement('div');
                wrap.className = 'text-xs sm:text-sm text-slate-600 dark:text-slate-400 border-l-2 border-primary-400 pl-2 py-1 my-0.5';
                wrap.textContent = String(item.content || '');
                stepsEl.appendChild(wrap);
                scrollChatToBottom();

            } else if (item.type === 'done') {
                done = true;
                es.close();
                delete activeStreams[requestId];

                // item.content may be empty when "done" is only a stream-close signal after media.
                const finalText = item.content || accumulatedText;

                if (!botEl && finalText) {
                    if (loadingEl) { loadingEl.remove(); loadingEl = null; }
                    addBotMessage(finalText, new Date((item.timestamp || Date.now() / 1000) * 1000), requestId);
                } else if (botEl) {
                    contentEl.classList.remove('sse-streaming');
                    if (finalText) contentEl.innerHTML = renderMarkdown(finalText);
                    contentEl.dataset.rawMd = finalText || '';
                    const copyBtn = botEl.querySelector('.copy-msg-btn');
                    if (copyBtn && finalText) copyBtn.style.display = '';
                    applyHighlighting(botEl);
                }
                scrollChatToBottom();

                if (titleInfo) {
                    generateSessionTitle(titleInfo.sid, titleInfo.userMsg, '');
                    titleInfo = null;
                } else if (sessionPanelOpen) {
                    loadSessionList();
                }

            } else if (item.type === 'error') {
                done = true;
                es.close();
                delete activeStreams[requestId];
                if (loadingEl) { loadingEl.remove(); loadingEl = null; }
                addBotMessage(t('error_send'), new Date());
            }
        };

        es.onerror = function() {
            es.close();
            delete activeStreams[requestId];

            if (done) return;

            if (currentReasoningEl) {
                finalizeThinking(currentReasoningEl, reasoningStartTime, reasoningText);
                currentReasoningEl = null;
                reasoningText = '';
            }

            if (reconnectCount < MAX_RECONNECTS) {
                reconnectCount++;
                const delay = Math.min(RECONNECT_BASE_MS * reconnectCount, 5000);
                console.warn(`[SSE] connection lost for ${requestId}, reconnecting in ${delay}ms (attempt ${reconnectCount}/${MAX_RECONNECTS})`);
                setTimeout(connect, delay);
                return;
            }

            // Exhausted retries, show whatever we have
            if (loadingEl) { loadingEl.remove(); loadingEl = null; }
            if (!botEl) {
                addBotMessage(t('error_send'), new Date());
            } else if (accumulatedText) {
                contentEl.classList.remove('sse-streaming');
                contentEl.innerHTML = renderMarkdown(accumulatedText);
                applyHighlighting(botEl);
                bindChatKnowledgeLinks(botEl);
            }
        };
    }

    connect();
}

function startPolling() {
    const gen = ++pollGeneration;
    isPolling = true;
    let pollInFlight = false;

    function poll() {
        if (gen !== pollGeneration) return;
        if (pollInFlight) return;
        if (document.hidden) { setTimeout(poll, 10000); return; }

        pollInFlight = true;
        fetch('/poll', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(withAgentBody({ session_id: sessionId }))
        })
        .then(r => r.json())
        .then(data => {
            pollInFlight = false;
            if (gen !== pollGeneration) return;
            if (data.status === 'success' && data.has_content) {
                const rid = data.request_id;
                if (loadingContainers[rid]) {
                    loadingContainers[rid].remove();
                    delete loadingContainers[rid];
                }
                const welcomeScreen = document.getElementById('welcome-screen');
                if (welcomeScreen) welcomeScreen.remove();
                addBotMessage(data.content, new Date(data.timestamp * 1000), rid);
                scrollChatToBottom();
            }
            const delay = (data.status === 'success' && data.has_content) ? 5000 : 10000;
            setTimeout(poll, delay);
        })
        .catch(() => { pollInFlight = false; setTimeout(poll, 10000); });
    }
    poll();
}

function createUserMessageEl(content, timestamp, attachments) {
    const el = document.createElement('div');
    el.className = 'flex justify-end px-4 sm:px-6 py-3';

    let attachHtml = '';
    if (attachments && attachments.length > 0) {
        const items = attachments.map(a => {
            if (a.file_type === 'image') {
                return `<img src="${a.preview_url}" alt="${escapeHtml(a.file_name)}" class="user-msg-image">`;
            }
            const icon = a.file_type === 'video' ? 'fa-film' : 'fa-file-alt';
            return `<div class="user-msg-file"><i class="fas ${icon}"></i> ${escapeHtml(a.file_name)}</div>`;
        }).join('');
        attachHtml = `<div class="user-msg-attachments">${items}</div>`;
    }

    const textHtml = content ? renderMarkdown(content) : '';
    el.innerHTML = `
        <div class="max-w-[75%] sm:max-w-[60%]">
            <div class="bg-primary-400 text-white rounded-2xl px-4 py-2.5 text-sm leading-relaxed msg-content user-bubble">
                ${attachHtml}${textHtml}
            </div>
            <div class="text-xs text-slate-400 dark:text-slate-500 mt-1.5 text-right">${formatTime(timestamp)}</div>
        </div>
    `;
    return el;
}

function renderToolCallsHtml(toolCalls) {
    if (!toolCalls || toolCalls.length === 0) return '';
    return toolCalls.map(tc => {
        const argsStr = formatToolArgs(tc.arguments || {});
        const resultStr = tc.result ? escapeHtml(String(tc.result)) : '';
        const hasResult = !!resultStr;
        return `
<div class="agent-step agent-tool-step">
    <div class="tool-header" onclick="this.parentElement.classList.toggle('expanded')">
        <i class="fas fa-check text-primary-400 flex-shrink-0 tool-icon"></i>
        <span class="tool-name">${escapeHtml(tc.name || '')}</span>
        <i class="fas fa-chevron-right tool-chevron"></i>
    </div>
    <div class="tool-detail">
        <div class="tool-detail-section">
            <div class="tool-detail-label">Input</div>
            <pre class="tool-detail-content">${argsStr}</pre>
        </div>
        ${hasResult ? `
        <div class="tool-detail-section tool-output-section">
            <div class="tool-detail-label">Output</div>
            <pre class="tool-detail-content">${resultStr}</pre>
        </div>` : ''}
    </div>
</div>`;
    }).join('');
}

function finalizeThinking(el, startTime, text) {
    const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);
    el.querySelector('.thinking-summary').textContent = t('thinking_done');
    const fullDiv = el.querySelector('.thinking-full');
    fullDiv.innerHTML = `<div class="thinking-duration">${t('thinking_duration')} ${elapsed}s</div>` + renderMarkdown(text);
}

function renderThinkingHtml(text) {
    if (!text || !text.trim()) return '';
    const full = text.trim();
    return `
<div class="agent-step agent-thinking-step">
    <div class="thinking-header" onclick="this.parentElement.classList.toggle('expanded')">
        <i class="fas fa-lightbulb text-amber-400 flex-shrink-0"></i>
        <span class="thinking-summary">${t('thinking_done')}</span>
        <i class="fas fa-chevron-right thinking-chevron"></i>
    </div>
    <div class="thinking-full">${renderMarkdown(full)}</div>
</div>`;
}

function renderStepsHtml(steps) {
    if (!steps || steps.length === 0) return { stepsHtml: '', finalContent: '' };

    // Find the index of the last content step — it becomes the main answer, not a step
    let lastContentIdx = -1;
    for (let i = steps.length - 1; i >= 0; i--) {
        if (steps[i].type === 'content') { lastContentIdx = i; break; }
    }

    let html = '';
    let lastContentText = '';
    for (let i = 0; i < steps.length; i++) {
        const step = steps[i];
        if (step.type === 'thinking') {
            html += renderThinkingHtml(step.content);
        } else if (step.type === 'content') {
            if (i === lastContentIdx) {
                lastContentText = step.content;
            } else {
                html += `<div class="agent-step agent-content-step"><div class="agent-content-body">${renderMarkdown(step.content)}</div></div>`;
            }
        } else if (step.type === 'tool') {
            const argsStr = formatToolArgs(step.arguments || {});
            const resultStr = step.result ? escapeHtml(String(step.result)) : '';
            html += `
<div class="agent-step agent-tool-step">
    <div class="tool-header" onclick="this.parentElement.classList.toggle('expanded')">
        <i class="fas fa-check text-primary-400 flex-shrink-0 tool-icon"></i>
        <span class="tool-name">${escapeHtml(step.name || '')}</span>
        <i class="fas fa-chevron-right tool-chevron"></i>
    </div>
    <div class="tool-detail">
        <div class="tool-detail-section">
            <div class="tool-detail-label">Input</div>
            <pre class="tool-detail-content">${argsStr}</pre>
        </div>
        ${resultStr ? `
        <div class="tool-detail-section tool-output-section">
            <div class="tool-detail-label">Output</div>
            <pre class="tool-detail-content">${resultStr}</pre>
        </div>` : ''}
    </div>
</div>`;
        }
    }
    return { stepsHtml: html, lastContentText };
}

function createBotMessageEl(content, timestamp, requestId, msg) {
    const el = document.createElement('div');
    el.className = 'flex gap-3 px-4 sm:px-6 py-3';
    if (requestId) el.dataset.requestId = requestId;

    let stepsHtml = '';
    let displayContent = content;

    if (msg && msg.steps && msg.steps.length > 0) {
        // New format: ordered steps with interleaved content
        const result = renderStepsHtml(msg.steps);
        stepsHtml = result.stepsHtml;
        // The final content (last text after all steps) is the main answer
        displayContent = content || result.lastContentText;
    } else {
        // Legacy format: separate tool_calls + optional reasoning
        const toolCalls = msg && msg.tool_calls;
        const reasoning = msg && msg.reasoning;
        stepsHtml = renderThinkingHtml(reasoning) + renderToolCallsHtml(toolCalls);
    }

    el.innerHTML = `
        <img src="assets/logo.jpg" alt="CowAgent" class="w-8 h-8 rounded-lg flex-shrink-0">
        <div class="min-w-0 flex-1 max-w-[85%]">
            <div class="bg-white dark:bg-[#1A1A1A] border border-slate-200 dark:border-white/10 rounded-2xl px-4 py-3 text-sm leading-relaxed msg-content text-slate-700 dark:text-slate-200">
                ${stepsHtml ? `<div class="agent-steps">${stepsHtml}</div>` : ''}
                <div class="answer-content">${renderMarkdown(displayContent)}</div>
            </div>
            <div class="flex items-center gap-2 mt-1.5">
                <span class="text-xs text-slate-400 dark:text-slate-500">${formatTime(timestamp)}</span>
                <button class="copy-msg-btn text-xs text-slate-300 dark:text-slate-600 hover:text-slate-500 dark:hover:text-slate-400 transition-colors cursor-pointer" title="${currentLang === 'zh' ? '复制' : 'Copy'}">
                    <i class="fas fa-copy"></i>
                </button>
            </div>
        </div>
    `;
    el.querySelector('.answer-content').dataset.rawMd = displayContent;
    applyHighlighting(el);
    bindChatKnowledgeLinks(el);
    return el;
}

function addUserMessage(content, timestamp, attachments) {
    const el = createUserMessageEl(content, timestamp, attachments);
    messagesDiv.appendChild(el);
    scrollChatToBottom();
}

function addBotMessage(content, timestamp, requestId) {
    const el = createBotMessageEl(content, timestamp, requestId);
    messagesDiv.appendChild(el);
    scrollChatToBottom();
}

// Load conversation history from the server (page 1 = most recent messages).
// Subsequent pages prepend older messages when the user scrolls to the top.
function loadHistory(page) {
    if (historyLoading) return;
    historyLoading = true;

    fetch(appendAgentQuery(`/api/history?session_id=${encodeURIComponent(sessionId)}&page=${page}&page_size=20`))
        .then(r => r.json())
        .then(data => {
            if (data.status !== 'success' || data.messages.length === 0) return;

            const prevScrollHeight = messagesDiv.scrollHeight;
            const isFirstLoad = page === 1;

            // On first load, remove the welcome screen if history exists
            if (isFirstLoad) {
                const ws = document.getElementById('welcome-screen');
                if (ws) ws.remove();
            }

            // Build a fragment of history message elements in chronological order
            const fragment = document.createDocumentFragment();

            if (data.has_more && page > 1) {
                // Keep the "load more" sentinel in place (inserted below)
            }

            const ctxStartSeq = data.context_start_seq || 0;
            let dividerInserted = false;

            data.messages.forEach(msg => {
                const hasContent = msg.content && msg.content.trim();
                const hasToolCalls = msg.role === 'assistant' && msg.tool_calls && msg.tool_calls.length > 0;
                if (!hasContent && !hasToolCalls) return;

                // Insert context divider when transitioning from above to below boundary
                if (ctxStartSeq > 0 && !dividerInserted && msg._seq !== undefined && msg._seq >= ctxStartSeq) {
                    dividerInserted = true;
                    const divider = document.createElement('div');
                    divider.className = 'context-divider';
                    divider.innerHTML = `<span>${t('context_cleared')}</span>`;
                    fragment.appendChild(divider);
                }

                const ts = new Date(msg.created_at * 1000);
                const el = msg.role === 'user'
                    ? createUserMessageEl(msg.content, ts)
                    : createBotMessageEl(msg.content || '', ts, null, msg);
                fragment.appendChild(el);
            });

            // If context was cleared but no new messages exist yet, append divider at the end
            if (ctxStartSeq > 0 && !dividerInserted) {
                const divider = document.createElement('div');
                divider.className = 'context-divider';
                divider.innerHTML = `<span>${t('context_cleared')}</span>`;
                fragment.appendChild(divider);
            }

            // Prepend history above any existing messages
            const sentinel = document.getElementById('history-load-more');
            const insertBefore = sentinel ? sentinel.nextSibling : messagesDiv.firstChild;
            messagesDiv.insertBefore(fragment, insertBefore);

            // Manage the "load more" sentinel at the very top
            if (data.has_more) {
                if (!document.getElementById('history-load-more')) {
                    const btn = document.createElement('div');
                    btn.id = 'history-load-more';
                    btn.className = 'flex justify-center py-3';
                    btn.innerHTML = `<button class="text-xs text-slate-400 dark:text-slate-500 hover:text-primary-400 transition-colors" onclick="loadHistory(historyPage + 1)">Load earlier messages</button>`;
                    messagesDiv.insertBefore(btn, messagesDiv.firstChild);
                }
            } else {
                const sentinel = document.getElementById('history-load-more');
                if (sentinel) sentinel.remove();
            }

            historyHasMore = data.has_more;
            historyPage = page;

            if (isFirstLoad) {
                // Use requestAnimationFrame to ensure the DOM has fully rendered
                // before scrolling, otherwise scrollHeight may not reflect new content.
                requestAnimationFrame(() => scrollChatToBottom());
            } else {
                // Restore scroll position so loading older messages doesn't jump the view
                messagesDiv.scrollTop = messagesDiv.scrollHeight - prevScrollHeight;
            }
        })
        .catch(() => {})
        .finally(() => { historyLoading = false; });
}

function addLoadingIndicator() {
    const el = document.createElement('div');
    el.className = 'flex gap-3 px-4 sm:px-6 py-3';
    el.innerHTML = `
        <img src="assets/logo.jpg" alt="CowAgent" class="w-8 h-8 rounded-lg flex-shrink-0">
        <div class="bg-white dark:bg-[#1A1A1A] border border-slate-200 dark:border-white/10 rounded-2xl px-4 py-3">
            <div class="flex items-center gap-1.5">
                <span class="w-2 h-2 rounded-full bg-primary-400 animate-pulse-dot" style="animation-delay: 0s"></span>
                <span class="w-2 h-2 rounded-full bg-primary-400 animate-pulse-dot" style="animation-delay: 0.2s"></span>
                <span class="w-2 h-2 rounded-full bg-primary-400 animate-pulse-dot" style="animation-delay: 0.4s"></span>
            </div>
        </div>
    `;
    messagesDiv.appendChild(el);
    scrollChatToBottom();
    return el;
}

function newChat() {
    // Close all active SSE connections for the current session
    Object.values(activeStreams).forEach(es => { try { es.close(); } catch (_) {} });
    activeStreams = {};

    // Generate a fresh session and persist it so the next page load also starts clean
    sessionId = generateSessionId();
    localStorage.setItem(SESSION_ID_KEY, sessionId);
    loadingContainers = {};
    startPolling();  // bump generation so old loop self-cancels, new loop uses fresh sessionId
    messagesDiv.innerHTML = '';
    const ws = document.createElement('div');
    ws.id = 'welcome-screen';
    ws.className = 'flex flex-col items-center justify-center h-full px-6 pb-16';
    ws.style.paddingTop = '6vh';
    ws.innerHTML = `
        <img src="assets/logo.jpg" alt="CowAgent" class="w-16 h-16 rounded-2xl mb-6 shadow-lg shadow-primary-500/20">
        <h1 class="text-2xl font-bold text-slate-800 dark:text-slate-100 mb-3">${appConfig.title || 'CowAgent'}</h1>
        <p class="text-slate-500 dark:text-slate-400 text-center max-w-lg mb-10 leading-relaxed" data-i18n="welcome_subtitle">${t('welcome_subtitle')}</p>
        <div class="grid grid-cols-2 sm:grid-cols-3 gap-3 w-full max-w-2xl">
            <div class="example-card group bg-white dark:bg-[#1A1A1A] border border-slate-200 dark:border-white/10 rounded-xl p-4 cursor-pointer hover:border-primary-300 dark:hover:border-primary-600 hover:shadow-md transition-all duration-200">
                <div class="flex items-center gap-2 mb-2">
                    <div class="w-7 h-7 rounded-lg bg-blue-50 dark:bg-blue-900/30 flex items-center justify-center">
                        <i class="fas fa-folder-open text-blue-500 text-xs"></i>
                    </div>
                    <span class="font-medium text-sm text-slate-700 dark:text-slate-200" data-i18n="example_sys_title">${t('example_sys_title')}</span>
                </div>
                <p class="text-sm text-slate-500 dark:text-slate-400 leading-relaxed" data-i18n="example_sys_text">${t('example_sys_text')}</p>
            </div>
            <div class="example-card group bg-white dark:bg-[#1A1A1A] border border-slate-200 dark:border-white/10 rounded-xl p-4 cursor-pointer hover:border-primary-300 dark:hover:border-primary-600 hover:shadow-md transition-all duration-200">
                <div class="flex items-center gap-2 mb-2">
                    <div class="w-7 h-7 rounded-lg bg-amber-50 dark:bg-amber-900/30 flex items-center justify-center">
                        <i class="fas fa-clock text-amber-500 text-xs"></i>
                    </div>
                    <span class="font-medium text-sm text-slate-700 dark:text-slate-200" data-i18n="example_task_title">${t('example_task_title')}</span>
                </div>
                <p class="text-sm text-slate-500 dark:text-slate-400 leading-relaxed" data-i18n="example_task_text">${t('example_task_text')}</p>
            </div>
            <div class="example-card group bg-white dark:bg-[#1A1A1A] border border-slate-200 dark:border-white/10 rounded-xl p-4 cursor-pointer hover:border-primary-300 dark:hover:border-primary-600 hover:shadow-md transition-all duration-200">
                <div class="flex items-center gap-2 mb-2">
                    <div class="w-7 h-7 rounded-lg bg-emerald-50 dark:bg-emerald-900/30 flex items-center justify-center">
                        <i class="fas fa-code text-emerald-500 text-xs"></i>
                    </div>
                    <span class="font-medium text-sm text-slate-700 dark:text-slate-200" data-i18n="example_code_title">${t('example_code_title')}</span>
                </div>
                <p class="text-sm text-slate-500 dark:text-slate-400 leading-relaxed" data-i18n="example_code_text">${t('example_code_text')}</p>
            </div>
            <div class="example-card group bg-white dark:bg-[#1A1A1A] border border-slate-200 dark:border-white/10 rounded-xl p-4 cursor-pointer hover:border-primary-300 dark:hover:border-primary-600 hover:shadow-md transition-all duration-200">
                <div class="flex items-center gap-2 mb-2">
                    <div class="w-7 h-7 rounded-lg bg-violet-50 dark:bg-violet-900/30 flex items-center justify-center">
                        <i class="fas fa-book text-violet-500 text-xs"></i>
                    </div>
                    <span class="font-medium text-sm text-slate-700 dark:text-slate-200" data-i18n="example_knowledge_title">${t('example_knowledge_title')}</span>
                </div>
                <p class="text-sm text-slate-500 dark:text-slate-400 leading-relaxed" data-i18n="example_knowledge_text">${t('example_knowledge_text')}</p>
            </div>
            <div class="example-card group bg-white dark:bg-[#1A1A1A] border border-slate-200 dark:border-white/10 rounded-xl p-4 cursor-pointer hover:border-primary-300 dark:hover:border-primary-600 hover:shadow-md transition-all duration-200">
                <div class="flex items-center gap-2 mb-2">
                    <div class="w-7 h-7 rounded-lg bg-rose-50 dark:bg-rose-900/30 flex items-center justify-center">
                        <i class="fas fa-puzzle-piece text-rose-500 text-xs"></i>
                    </div>
                    <span class="font-medium text-sm text-slate-700 dark:text-slate-200" data-i18n="example_skill_title">${t('example_skill_title')}</span>
                </div>
                <p class="text-sm text-slate-500 dark:text-slate-400 leading-relaxed" data-i18n="example_skill_text">${t('example_skill_text')}</p>
            </div>
            <div class="example-card group bg-white dark:bg-[#1A1A1A] border border-slate-200 dark:border-white/10 rounded-xl p-4 cursor-pointer hover:border-primary-300 dark:hover:border-primary-600 hover:shadow-md transition-all duration-200" data-send="/help">
                <div class="flex items-center gap-2 mb-2">
                    <div class="w-7 h-7 rounded-lg bg-slate-100 dark:bg-slate-800 flex items-center justify-center">
                        <i class="fas fa-terminal text-slate-500 text-xs"></i>
                    </div>
                    <span class="font-medium text-sm text-slate-700 dark:text-slate-200" data-i18n="example_web_title">${t('example_web_title')}</span>
                </div>
                <p class="text-sm text-slate-500 dark:text-slate-400 leading-relaxed" data-i18n="example_web_text">${t('example_web_text')}</p>
            </div>
        </div>
    `;
    messagesDiv.appendChild(ws);
    ws.querySelectorAll('.example-card').forEach(card => {
        card.addEventListener('click', () => {
            const sendText = card.dataset.send;
            if (sendText) {
                chatInput.value = sendText;
                chatInput.dispatchEvent(new Event('input'));
                chatInput.focus();
                return;
            }
            const textEl = card.querySelector('[data-i18n*="text"]');
            if (textEl) {
                chatInput.value = textEl.textContent;
                chatInput.dispatchEvent(new Event('input'));
                chatInput.focus();
            }
        });
    });
    if (currentView !== 'chat') navigateTo('chat');

    // Show panel and load full session list, then prepend the new session on top
    const panel = document.getElementById('session-panel');
    if (panel && !sessionPanelOpen) {
        sessionPanelOpen = true;
        panel.classList.remove('hidden');
        _persistPanelState();
    }
    const newSid = sessionId;
    loadSessionList(() => _addOptimisticSessionItem(newSid));
}

// =====================================================================
// Session Panel
// =====================================================================

const SESSION_PANEL_KEY = 'cow_session_panel_open';
let sessionPanelOpen = localStorage.getItem(SESSION_PANEL_KEY) === '1';

function _persistPanelState() {
    localStorage.setItem(SESSION_PANEL_KEY, sessionPanelOpen ? '1' : '0');
}

function toggleSessionPanel() {
    const panel = document.getElementById('session-panel');
    if (!panel) return;
    sessionPanelOpen = !sessionPanelOpen;
    panel.classList.toggle('hidden', !sessionPanelOpen);
    _persistPanelState();
    if (sessionPanelOpen) loadSessionList();
}

function openSessionPanel() {
    const panel = document.getElementById('session-panel');
    if (!panel || sessionPanelOpen) return;
    sessionPanelOpen = true;
    panel.classList.remove('hidden');
    _persistPanelState();
    loadSessionList();
}

function _restoreSessionPanel() {
    const panel = document.getElementById('session-panel');
    if (!panel) return;
    if (sessionPanelOpen) {
        panel.classList.remove('hidden');
        loadSessionList();
    } else {
        panel.classList.add('hidden');
    }
}

function _applyInputTooltips() {
    const set = (id, key, pos) => {
        const el = document.getElementById(id);
        if (!el) return;
        el.setAttribute('data-tooltip', t(key));
        el.removeAttribute('title');
        if (pos) el.setAttribute('data-tooltip-pos', pos);
    };
    set('new-chat-btn', 'tip_new_chat');
    set('clear-context-btn', 'tip_clear_context');
    set('attach-btn', 'tip_attach_file');
    set('session-toggle-btn', 'session_history', 'bottom');
}

function _addOptimisticSessionItem(sid) {
    const container = document.getElementById('session-list');
    if (!container) return;

    const emptyEl = container.querySelector('.session-empty');
    if (emptyEl) emptyEl.remove();

    document.querySelectorAll('.session-item.active').forEach(el => el.classList.remove('active'));

    const todayLabel = t('today');
    let firstGroup = container.querySelector('.session-group-label');
    if (!firstGroup || firstGroup.textContent !== todayLabel) {
        const header = document.createElement('div');
        header.className = 'session-group-label';
        header.textContent = todayLabel;
        container.prepend(header);
        firstGroup = header;
    }

    const title = t('new_chat');
    const item = document.createElement('div');
    item.className = 'session-item active';
    item.dataset.sessionId = sid;
    item.innerHTML = `
        <i class="fas fa-message session-icon"></i>
        <span class="session-title" title="${escapeHtml(title)}">${escapeHtml(title)}</span>
        <button class="session-delete" onclick="event.stopPropagation(); deleteSession('${sid}')" title="Delete">
            <i class="fas fa-trash-can"></i>
        </button>
    `;
    item.addEventListener('click', () => switchSession(sid));
    firstGroup.insertAdjacentElement('afterend', item);
}

function _sessionTimeGroup(ts) {
    const now = new Date();
    const d = new Date(ts * 1000);
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const yesterday = new Date(today); yesterday.setDate(today.getDate() - 1);
    if (d >= today) return t('today');
    if (d >= yesterday) return t('yesterday');
    return t('earlier');
}

let _sessionPage = 1;
let _sessionHasMore = false;
let _sessionLoading = false;
const _SESSION_PAGE_SIZE = 50;

function loadSessionList(onDone) {
    const container = document.getElementById('session-list');
    if (!container) return;

    _sessionPage = 1;
    _sessionHasMore = false;

    _fetchSessionPage(1, true, onDone);
}

function _fetchSessionPage(page, clear, onDone) {
    if (_sessionLoading) return;
    _sessionLoading = true;

    const container = document.getElementById('session-list');
    if (!container) { _sessionLoading = false; return; }

    // Remove existing "load more" sentinel before fetching
    const oldSentinel = container.querySelector('.session-load-more');
    if (oldSentinel) oldSentinel.remove();

    fetch(appendAgentQuery(`/api/sessions?page=${page}&page_size=${_SESSION_PAGE_SIZE}`))
        .then(r => r.json())
        .then(data => {
            _sessionLoading = false;
            if (data.status !== 'success') return;

            if (clear) container.innerHTML = '';

            const sessions = data.sessions || [];
            _sessionPage = page;
            _sessionHasMore = !!data.has_more;

            if (sessions.length === 0 && page === 1) {
                container.innerHTML = '<div class="session-empty">' + t('untitled_session') + '</div>';
                if (typeof onDone === 'function') onDone();
                return;
            }

            // Track last group label already in the container
            const existingLabels = container.querySelectorAll('.session-group-label');
            let lastGroup = existingLabels.length > 0
                ? existingLabels[existingLabels.length - 1].textContent
                : '';

            sessions.forEach(s => {
                const group = _sessionTimeGroup(s.last_active);
                if (group !== lastGroup) {
                    lastGroup = group;
                    const header = document.createElement('div');
                    header.className = 'session-group-label';
                    header.textContent = group;
                    container.appendChild(header);
                }

                const item = document.createElement('div');
                const isActive = s.session_id === sessionId;
                item.className = 'session-item' + (isActive ? ' active' : '');
                item.dataset.sessionId = s.session_id;

                const title = s.title || t('untitled_session');
                item.innerHTML = `
                    <i class="fas fa-message session-icon"></i>
                    <span class="session-title" title="${escapeHtml(title)}">${escapeHtml(title)}</span>
                    <button class="session-delete" onclick="event.stopPropagation(); deleteSession('${s.session_id}')" title="Delete">
                        <i class="fas fa-trash-can"></i>
                    </button>
                `;
                item.addEventListener('click', () => switchSession(s.session_id));
                container.appendChild(item);
            });

            if (typeof onDone === 'function') onDone();
        })
        .catch(() => { _sessionLoading = false; });
}

function _onSessionListScroll() {
    if (!_sessionHasMore || _sessionLoading) return;
    const container = document.getElementById('session-list');
    if (!container) return;
    // Trigger when scrolled near the bottom (within 60px)
    if (container.scrollHeight - container.scrollTop - container.clientHeight < 60) {
        _fetchSessionPage(_sessionPage + 1, false);
    }
}

// Attach scroll listener once DOM is ready
(function _initSessionScroll() {
    const el = document.getElementById('session-list');
    if (el) {
        el.addEventListener('scroll', _onSessionListScroll);
    } else {
        document.addEventListener('DOMContentLoaded', () => {
            const el2 = document.getElementById('session-list');
            if (el2) el2.addEventListener('scroll', _onSessionListScroll);
        });
    }
})();

function switchSession(newSessionId) {
    if (newSessionId === sessionId) {
        if (currentView !== 'chat') navigateTo('chat');
        return;
    }

    Object.values(activeStreams).forEach(es => { try { es.close(); } catch (_) {} });
    activeStreams = {};
    loadingContainers = {};

    sessionId = newSessionId;
    localStorage.setItem(SESSION_ID_KEY, sessionId);

    historyPage = 0;
    historyHasMore = false;
    historyLoading = false;

    messagesDiv.innerHTML = '';
    loadHistory(1);
    startPolling();

    document.querySelectorAll('.session-item').forEach(el => {
        el.classList.toggle('active', el.dataset.sessionId === sessionId);
    });

    if (currentView !== 'chat') navigateTo('chat');
}

function deleteSession(sid) {
    showConfirmModal(t('delete_session_title'), t('delete_session_confirm'), () => {
        fetch(appendAgentQuery(`/api/sessions/${encodeURIComponent(sid)}`), { method: 'DELETE' })
            .then(r => r.json())
            .then(data => {
                if (data.status !== 'success') return;
                if (sid === sessionId) {
                    newChat();
                } else {
                    loadSessionList();
                }
            })
            .catch(() => {});
    });
}

function showConfirmModal(title, message, onConfirm) {
    let overlay = document.getElementById('confirm-modal-overlay');
    if (overlay) overlay.remove();

    overlay = document.createElement('div');
    overlay.id = 'confirm-modal-overlay';
    overlay.className = 'confirm-overlay';

    const modal = document.createElement('div');
    modal.className = 'confirm-modal';
    modal.innerHTML = `
        <div class="confirm-title">${escapeHtml(title)}</div>
        <div class="confirm-message">${escapeHtml(message)}</div>
        <div class="confirm-actions">
            <button class="confirm-btn confirm-btn-cancel">${t('confirm_cancel')}</button>
            <button class="confirm-btn confirm-btn-ok">${t('confirm_yes')}</button>
        </div>
    `;
    overlay.appendChild(modal);
    document.body.appendChild(overlay);

    requestAnimationFrame(() => overlay.classList.add('visible'));

    const close = () => {
        overlay.classList.remove('visible');
        setTimeout(() => overlay.remove(), 200);
    };

    overlay.addEventListener('click', (e) => { if (e.target === overlay) close(); });
    modal.querySelector('.confirm-btn-cancel').addEventListener('click', close);
    modal.querySelector('.confirm-btn-ok').addEventListener('click', () => {
        close();
        onConfirm();
    });
}

function clearContext() {
    fetch(appendAgentQuery(`/api/sessions/${encodeURIComponent(sessionId)}/clear_context`), { method: 'POST' })
        .then(r => r.json())
        .then(data => {
            if (data.status !== 'success') return;
            // Insert a visual divider in the chat
            const divider = document.createElement('div');
            divider.className = 'context-divider';
            divider.innerHTML = `<span>${t('context_cleared')}</span>`;
            messagesDiv.appendChild(divider);
            scrollChatToBottom();
        })
        .catch(() => {});
}

function generateSessionTitle(sid, userMsg, assistantReply) {
    fetch(`/api/sessions/${encodeURIComponent(sid)}/generate_title`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(withAgentBody({ user_message: userMsg, assistant_reply: assistantReply })),
    })
        .then(r => r.json())
        .then(data => {
            if (data.status === 'success' && sessionPanelOpen) {
                loadSessionList();
            }
        })
        .catch(() => {});
}

// =====================================================================
// Utilities
// =====================================================================
function formatTime(date) {
    const now = new Date();
    const sameDay = date.getFullYear() === now.getFullYear()
        && date.getMonth() === now.getMonth()
        && date.getDate() === now.getDate();
    const time = date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    if (sameDay) return time;
    const m = String(date.getMonth() + 1).padStart(2, '0');
    const d = String(date.getDate()).padStart(2, '0');
    if (date.getFullYear() === now.getFullYear()) return `${m}-${d} ${time}`;
    return `${date.getFullYear()}-${m}-${d} ${time}`;
}

function escapeHtml(str) {
    const div = document.createElement('div');
    div.appendChild(document.createTextNode(str));
    return div.innerHTML;
}

function ChannelsHandler_maskSecret(val) {
    if (!val || val.length <= 8) return val;
    return val.slice(0, 4) + '*'.repeat(val.length - 8) + val.slice(-4);
}

function formatToolArgs(args) {
    if (!args || Object.keys(args).length === 0) return '(none)';
    try {
        return escapeHtml(JSON.stringify(args, null, 2));
    } catch (_) {
        return escapeHtml(String(args));
    }
}

function scrollChatToBottom() {
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

function applyHighlighting(container) {
    const root = container || document;
    setTimeout(() => {
        root.querySelectorAll('pre code').forEach(block => {
            if (!block.classList.contains('hljs')) {
                hljs.highlightElement(block);
            }
        });
    }, 0);
}

// =====================================================================
// Config View
// =====================================================================
let configProviders = {};
let configApiBases = {};
let configApiKeys = {};
let configCurrentModel = '';
let cfgProviderValue = '';
let cfgModelValue = '';

// --- Custom dropdown helper ---
function initDropdown(el, options, selectedValue, onChange) {
    const textEl = el.querySelector('.cfg-dropdown-text');
    const menuEl = el.querySelector('.cfg-dropdown-menu');
    const selEl = el.querySelector('.cfg-dropdown-selected');

    el._ddValue = selectedValue || '';
    el._ddOnChange = onChange;

    function render() {
        menuEl.innerHTML = '';
        options.forEach(opt => {
            const item = document.createElement('div');
            item.className = 'cfg-dropdown-item' + (opt.value === el._ddValue ? ' active' : '');
            item.textContent = opt.label;
            item.dataset.value = opt.value;
            item.addEventListener('click', (e) => {
                e.stopPropagation();
                el._ddValue = opt.value;
                textEl.textContent = opt.label;
                menuEl.querySelectorAll('.cfg-dropdown-item').forEach(i => i.classList.remove('active'));
                item.classList.add('active');
                el.classList.remove('open');
                if (el._ddOnChange) el._ddOnChange(opt.value);
            });
            menuEl.appendChild(item);
        });
        const sel = options.find(o => o.value === el._ddValue);
        textEl.textContent = sel ? sel.label : (options[0] ? options[0].label : '--');
        if (!sel && options[0]) el._ddValue = options[0].value;
    }

    render();

    if (!el._ddBound) {
        selEl.addEventListener('click', (e) => {
            e.stopPropagation();
            document.querySelectorAll('.cfg-dropdown.open').forEach(d => { if (d !== el) d.classList.remove('open'); });
            el.classList.toggle('open');
        });
        el._ddBound = true;
    }
}

document.addEventListener('click', () => {
    document.querySelectorAll('.cfg-dropdown.open').forEach(d => d.classList.remove('open'));
});

function getDropdownValue(el) { return el._ddValue || ''; }

// --- Config init ---
function initConfigView(data) {
    configProviders = data.providers || {};
    configApiBases = data.api_bases || {};
    configApiKeys = data.api_keys || {};
    configCurrentModel = data.model || '';

    const providerEl = document.getElementById('cfg-provider');
    const providerOpts = Object.entries(configProviders).map(([pid, p]) => ({ value: pid, label: p.label }));

    // if use_linkai is enabled, always select linkai as the provider
    // Otherwise prefer bot_type from config, fall back to model-based detection
    const detected = data.use_linkai ? 'linkai'
        : (data.bot_type && configProviders[data.bot_type] ? data.bot_type : detectProvider(configCurrentModel));
    cfgProviderValue = detected || (providerOpts[0] ? providerOpts[0].value : '');

    initDropdown(providerEl, providerOpts, cfgProviderValue, onProviderChange);

    onProviderChange(cfgProviderValue);
    syncModelSelection(configCurrentModel);

    document.getElementById('cfg-max-tokens').value = data.agent_max_context_tokens || 50000;
    document.getElementById('cfg-max-turns').value = data.agent_max_context_turns || 20;
    document.getElementById('cfg-max-steps').value = data.agent_max_steps || 20;
    document.getElementById('cfg-enable-thinking').checked = data.enable_thinking !== false;

    const pwdInput = document.getElementById('cfg-password');
    const maskedPwd = data.web_password_masked || '';
    pwdInput.value = maskedPwd;
    pwdInput.dataset.masked = maskedPwd ? '1' : '';
    pwdInput.dataset.maskedVal = maskedPwd;
    pwdInput.classList.toggle('cfg-key-masked', !!maskedPwd);

    if (maskedPwd) {
        pwdInput.placeholder = '••••••••';
    } else {
        pwdInput.placeholder = '';
    }

    if (!pwdInput._cfgBound) {
        pwdInput.addEventListener('focus', function() {
            if (this.dataset.masked === '1') {
                this.value = '';
                this.dataset.masked = '';
                this.classList.remove('cfg-key-masked');
            }
        });
        pwdInput.addEventListener('input', function() {
            this.dataset.masked = '';
        });
        pwdInput._cfgBound = true;
    }
}

function detectProvider(model) {
    if (!model) return Object.keys(configProviders)[0] || '';
    for (const [pid, p] of Object.entries(configProviders)) {
        if (pid === 'linkai') continue;
        if (p.models && p.models.includes(model)) return pid;
    }
    return Object.keys(configProviders)[0] || '';
}

function onProviderChange(pid) {
    cfgProviderValue = pid || getDropdownValue(document.getElementById('cfg-provider'));
    const p = configProviders[cfgProviderValue];
    if (!p) return;

    const modelEl = document.getElementById('cfg-model-select');
    const modelOpts = (p.models || []).map(m => ({ value: m, label: m }));
    modelOpts.push({ value: '__custom__', label: t('config_custom_option') });

    initDropdown(modelEl, modelOpts, modelOpts[0] ? modelOpts[0].value : '', onModelSelectChange);

    // API Key
    const keyField = p.api_key_field;
    const keyWrap = document.getElementById('cfg-api-key-wrap');
    const keyInput = document.getElementById('cfg-api-key');
    if (keyField) {
        keyWrap.classList.remove('hidden');
        keyInput.classList.add('cfg-key-masked');
        const maskedVal = configApiKeys[keyField] || '';
        keyInput.value = maskedVal;
        keyInput.dataset.field = keyField;
        keyInput.dataset.masked = maskedVal ? '1' : '';
        keyInput.dataset.maskedVal = maskedVal;
        const toggleIcon = document.querySelector('#cfg-api-key-toggle i');
        if (toggleIcon) toggleIcon.className = 'fas fa-eye text-xs';

        if (!keyInput._cfgBound) {
            keyInput.addEventListener('focus', function() {
                if (this.dataset.masked === '1') {
                    this.value = '';
                    this.dataset.masked = '';
                    this.classList.remove('cfg-key-masked');
                }
            });
            keyInput.addEventListener('blur', function() {
                if (!this.value.trim() && this.dataset.maskedVal) {
                    this.value = this.dataset.maskedVal;
                    this.dataset.masked = '1';
                    this.classList.add('cfg-key-masked');
                }
            });
            keyInput.addEventListener('input', function() {
                this.dataset.masked = '';
            });
            keyInput._cfgBound = true;
        }
    } else {
        keyWrap.classList.add('hidden');
        keyInput.value = '';
        keyInput.dataset.field = '';
    }

    // API Base
    if (p.api_base_key) {
        document.getElementById('cfg-api-base-wrap').classList.remove('hidden');
        document.getElementById('cfg-api-base').value = configApiBases[p.api_base_key] || p.api_base_default || '';
    } else {
        document.getElementById('cfg-api-base-wrap').classList.add('hidden');
        document.getElementById('cfg-api-base').value = '';
    }

    onModelSelectChange(modelOpts[0] ? modelOpts[0].value : '');
}

function onModelSelectChange(val) {
    cfgModelValue = val || getDropdownValue(document.getElementById('cfg-model-select'));
    const customWrap = document.getElementById('cfg-model-custom-wrap');
    if (cfgModelValue === '__custom__') {
        customWrap.classList.remove('hidden');
        document.getElementById('cfg-model-custom').focus();
    } else {
        customWrap.classList.add('hidden');
        document.getElementById('cfg-model-custom').value = '';
    }
}

function syncModelSelection(model) {
    const p = configProviders[cfgProviderValue];
    if (!p) return;

    const modelEl = document.getElementById('cfg-model-select');
    if (p.models && p.models.includes(model)) {
        const modelOpts = (p.models || []).map(m => ({ value: m, label: m }));
        modelOpts.push({ value: '__custom__', label: t('config_custom_option') });
        initDropdown(modelEl, modelOpts, model, onModelSelectChange);
        cfgModelValue = model;
        document.getElementById('cfg-model-custom-wrap').classList.add('hidden');
    } else {
        cfgModelValue = '__custom__';
        const modelOpts = (p.models || []).map(m => ({ value: m, label: m }));
        modelOpts.push({ value: '__custom__', label: t('config_custom_option') });
        initDropdown(modelEl, modelOpts, '__custom__', onModelSelectChange);
        document.getElementById('cfg-model-custom-wrap').classList.remove('hidden');
        document.getElementById('cfg-model-custom').value = model;
    }
}

function getSelectedModel() {
    if (cfgModelValue === '__custom__') {
        return document.getElementById('cfg-model-custom').value.trim();
    }
    return cfgModelValue;
}

function toggleApiKeyVisibility() {
    const input = document.getElementById('cfg-api-key');
    const icon = document.querySelector('#cfg-api-key-toggle i');
    if (input.classList.contains('cfg-key-masked')) {
        input.classList.remove('cfg-key-masked');
        icon.className = 'fas fa-eye-slash text-xs';
    } else {
        input.classList.add('cfg-key-masked');
        icon.className = 'fas fa-eye text-xs';
    }
}

function showStatus(elId, msgKey, isError) {
    const el = document.getElementById(elId);
    el.textContent = t(msgKey);
    el.classList.toggle('text-red-500', !!isError);
    el.classList.toggle('text-primary-500', !isError);
    el.classList.remove('opacity-0');
    setTimeout(() => el.classList.add('opacity-0'), 2500);
}

function saveModelConfig() {
    const model = getSelectedModel();
    if (!model) return;

    const updates = { model: model };
    const p = configProviders[cfgProviderValue];
    updates.use_linkai = (cfgProviderValue === 'linkai');
    if (cfgProviderValue === 'linkai') {
        updates.bot_type = '';
    } else {
        updates.bot_type = cfgProviderValue;
    }
    if (p && p.api_base_key) {
        const base = document.getElementById('cfg-api-base').value.trim();
        if (base) updates[p.api_base_key] = base;
    }
    if (p && p.api_key_field) {
        const keyInput = document.getElementById('cfg-api-key');
        const rawVal = keyInput.value.trim();
        if (rawVal && keyInput.dataset.masked !== '1') {
            updates[p.api_key_field] = rawVal;
        }
    }

    const btn = document.getElementById('cfg-model-save');
    btn.disabled = true;
    fetch('/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ updates })
    })
    .then(r => r.json())
    .then(data => {
        if (data.status === 'success') {
            configCurrentModel = model;
            if (data.applied) {
                const keyInput = document.getElementById('cfg-api-key');
                Object.entries(data.applied).forEach(([k, v]) => {
                    if (k === 'model') return;
                    if (k.includes('api_key')) {
                        const masked = v.length > 8
                            ? v.substring(0, 4) + '*'.repeat(v.length - 8) + v.substring(v.length - 4)
                            : v;
                        configApiKeys[k] = masked;
                        if (keyInput.dataset.field === k) {
                            keyInput.value = masked;
                            keyInput.dataset.masked = '1';
                            keyInput.dataset.maskedVal = masked;
                            keyInput.classList.add('cfg-key-masked');
                            const toggleIcon = document.querySelector('#cfg-api-key-toggle i');
                            if (toggleIcon) toggleIcon.className = 'fas fa-eye text-xs';
                        }
                    } else {
                        configApiBases[k] = v;
                    }
                });
            }
            showStatus('cfg-model-status', 'config_saved', false);
        } else {
            showStatus('cfg-model-status', 'config_save_error', true);
        }
    })
    .catch(() => showStatus('cfg-model-status', 'config_save_error', true))
    .finally(() => { btn.disabled = false; });
}

function saveAgentConfig() {
    const updates = {
        agent_max_context_tokens: parseInt(document.getElementById('cfg-max-tokens').value) || 50000,
        agent_max_context_turns: parseInt(document.getElementById('cfg-max-turns').value) || 20,
        agent_max_steps: parseInt(document.getElementById('cfg-max-steps').value) || 20,
        enable_thinking: document.getElementById('cfg-enable-thinking').checked,
    };

    const btn = document.getElementById('cfg-agent-save');
    btn.disabled = true;
    fetch('/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ updates })
    })
    .then(r => r.json())
    .then(data => {
        if (data.status === 'success') {
            showStatus('cfg-agent-status', 'config_saved', false);
        } else {
            showStatus('cfg-agent-status', 'config_save_error', true);
        }
    })
    .catch(() => showStatus('cfg-agent-status', 'config_save_error', true))
    .finally(() => { btn.disabled = false; });
}

function savePasswordConfig() {
    const input = document.getElementById('cfg-password');
    if (input.dataset.masked === '1') {
        showStatus('cfg-password-status', 'config_saved', false);
        return;
    }
    const newPwd = input.value.trim();
    const btn = document.getElementById('cfg-password-save');
    btn.disabled = true;
    fetch('/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ updates: { web_password: newPwd } })
    })
    .then(r => r.json())
    .then(data => {
        if (data.status === 'success') {
            if (newPwd) {
                showStatus('cfg-password-status', 'config_password_changed', false);
                setTimeout(() => { window.location.reload(); }, 1500);
            } else {
                input.dataset.masked = '';
                input.dataset.maskedVal = '';
                input.classList.remove('cfg-key-masked');
                showStatus('cfg-password-status', 'config_password_cleared', false);
            }
        } else {
            showStatus('cfg-password-status', 'config_save_error', true);
        }
    })
    .catch(() => showStatus('cfg-password-status', 'config_save_error', true))
    .finally(() => { btn.disabled = false; });
}

function loadConfigView() {
    fetch('/config').then(r => r.json()).then(data => {
        if (data.status !== 'success') return;
        appConfig = data;
        initConfigView(data);
    }).catch(() => {});
}

// =====================================================================
// Skills View
// =====================================================================
let toolsLoaded = false;

const TOOL_ICONS = {
    bash: 'fa-terminal',
    edit: 'fa-pen-to-square',
    read: 'fa-file-lines',
    write: 'fa-file-pen',
    ls: 'fa-folder-open',
    send: 'fa-paper-plane',
    web_search: 'fa-magnifying-glass',
    browser: 'fa-globe',
    env_config: 'fa-key',
    scheduler: 'fa-clock',
    memory_get: 'fa-brain',
    memory_search: 'fa-brain',
};

function getToolIcon(name) {
    return TOOL_ICONS[name] || 'fa-wrench';
}

function loadSkillsView() {
    loadToolsSection();
    loadSkillsSection();
}

function loadToolsSection() {
    if (toolsLoaded) return;
    const emptyEl = document.getElementById('tools-empty');
    const listEl = document.getElementById('tools-list');
    const badge = document.getElementById('tools-count-badge');

    fetch('/api/tools').then(r => r.json()).then(data => {
        if (data.status !== 'success') return;
        const tools = data.tools || [];
        emptyEl.classList.add('hidden');
        if (tools.length === 0) {
            emptyEl.classList.remove('hidden');
            emptyEl.innerHTML = `<span class="text-sm text-slate-400 dark:text-slate-500">${currentLang === 'zh' ? '暂无内置工具' : 'No built-in tools'}</span>`;
            return;
        }
        badge.textContent = tools.length;
        badge.classList.remove('hidden');
        listEl.innerHTML = '';
        tools.forEach(tool => {
            const card = document.createElement('div');
            card.className = 'bg-white dark:bg-[#1A1A1A] rounded-xl border border-slate-200 dark:border-white/10 p-4 flex items-start gap-3';
            card.innerHTML = `
                <div class="w-9 h-9 rounded-lg bg-blue-50 dark:bg-blue-900/20 flex items-center justify-center flex-shrink-0">
                    <i class="fas ${getToolIcon(tool.name)} text-blue-500 dark:text-blue-400 text-sm"></i>
                </div>
                <div class="flex-1 min-w-0">
                    <div class="flex items-center gap-2">
                        <span class="font-medium text-sm text-slate-700 dark:text-slate-200 font-mono">${escapeHtml(tool.name)}</span>
                    </div>
                    <p class="text-xs text-slate-400 dark:text-slate-500 mt-1 line-clamp-2">${escapeHtml(tool.description || '--')}</p>
                </div>`;
            listEl.appendChild(card);
        });
        listEl.classList.remove('hidden');
        toolsLoaded = true;
    }).catch(() => {
        emptyEl.classList.remove('hidden');
        emptyEl.innerHTML = `<span class="text-sm text-slate-400 dark:text-slate-500">${currentLang === 'zh' ? '加载失败' : 'Failed to load'}</span>`;
    });
}

function loadSkillsSection() {
    const emptyEl = document.getElementById('skills-empty');
    const listEl = document.getElementById('skills-list');
    const badge = document.getElementById('skills-count-badge');

    fetch(appendAgentQuery('/api/skills')).then(r => r.json()).then(data => {
        if (data.status !== 'success') return;
        const skills = data.skills || [];
        if (skills.length === 0) {
            const p = emptyEl.querySelector('p');
            if (p) p.textContent = currentLang === 'zh' ? '暂无技能' : 'No skills found';
            return;
        }
        badge.textContent = skills.length;
        badge.classList.remove('hidden');
        emptyEl.classList.add('hidden');
        listEl.innerHTML = '';

        skills.forEach(sk => {
            const card = document.createElement('div');
            card.className = 'bg-white dark:bg-[#1A1A1A] rounded-xl border border-slate-200 dark:border-white/10 p-4 flex items-start gap-3 transition-opacity';
            card.dataset.skillName = sk.name;
            card.dataset.skillDesc = sk.description || '';
            card.dataset.enabled = sk.enabled ? '1' : '0';
            renderSkillCard(card, sk);
            listEl.appendChild(card);
        });
    }).catch(() => {});
}

function renderSkillCard(card, sk) {
    const enabled = sk.enabled;
    const iconColor = enabled ? 'text-primary-400' : 'text-slate-300 dark:text-slate-600';
    const trackClass = enabled
        ? 'bg-primary-400'
        : 'bg-slate-200 dark:bg-slate-700';
    const thumbTranslate = enabled ? 'translate-x-3' : 'translate-x-0.5';
    card.innerHTML = `
        <div class="w-9 h-9 rounded-lg bg-amber-50 dark:bg-amber-900/20 flex items-center justify-center flex-shrink-0">
            <i class="fas fa-bolt ${iconColor} text-sm"></i>
        </div>
        <div class="flex-1 min-w-0">
            <div class="flex items-center gap-2 mb-1">
                <span class="font-medium text-sm text-slate-700 dark:text-slate-200 truncate flex-1">${escapeHtml(sk.display_name || sk.name)}</span>
                <button
                    role="switch"
                    aria-checked="${enabled}"
                    onclick="toggleSkill('${escapeHtml(sk.name)}', ${enabled})"
                    class="relative inline-flex h-4 w-7 flex-shrink-0 cursor-pointer rounded-full transition-colors duration-200 ease-in-out focus:outline-none ${trackClass}"
                    title="${enabled ? (currentLang === 'zh' ? '点击禁用' : 'Click to disable') : (currentLang === 'zh' ? '点击启用' : 'Click to enable')}"
                >
                    <span class="inline-block h-3 w-3 mt-0.5 rounded-full bg-white shadow transform transition-transform duration-200 ease-in-out ${thumbTranslate}"></span>
                </button>
            </div>
            <p class="text-xs text-slate-400 dark:text-slate-500 line-clamp-2">${escapeHtml(sk.description || '--')}</p>
        </div>`;
}

function toggleSkill(name, currentlyEnabled) {
    const action = currentlyEnabled ? 'close' : 'open';
    const card = document.querySelector(`[data-skill-name="${CSS.escape(name)}"]`);
    if (card) card.style.opacity = '0.5';

    fetch('/api/skills', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(withAgentBody({ action, name }))
    })
    .then(r => r.json())
    .then(data => {
        if (data.status === 'success') {
            if (card) {
                const desc = card.dataset.skillDesc || '';
                card.dataset.enabled = currentlyEnabled ? '0' : '1';
                card.style.opacity = '1';
                renderSkillCard(card, { name, description: desc, enabled: !currentlyEnabled });
            }
        } else {
            if (card) card.style.opacity = '1';
            alert(currentLang === 'zh' ? '操作失败，请稍后再试' : 'Operation failed, please try again');
        }
    })
    .catch(() => {
        if (card) card.style.opacity = '1';
        alert(currentLang === 'zh' ? '操作失败，请稍后再试' : 'Operation failed, please try again');
    });
}

// =====================================================================
// Agents View
// =====================================================================
const AVAILABLE_MODELS = [
    "gpt-4o", "gpt-4o-mini", "gpt-4-turbo",
    "claude-3-5-sonnet", "claude-3-5-haiku",
    "deepseek-chat", "deepseek-reasoner",
    "qwen-turbo", "qwen-plus", "qwen-max",
    "glm-4", "glm-4-flash",
    "moonshot-v1-8k", "moonshot-v1-32k",
    "doubao-pro-32k"
];

let _agentEditingId = null;         // null = create mode, string = edit mode
let _agentEditingTenantId = null;   // tenant context for edit mode
let _agentsLoadedFilterTenant = ''; // remember current filter in Agents view
let _agentToolsCache = [];          // cached tools list
let _agentSkillsCache = [];         // cached skills list

// =====================================================================
// Tenants & Tenant Users View
// =====================================================================
let _tenantEditingId = null;
let _tenantUserEditingKey = null;
let _tenantUserMeta = { roles: ['owner', 'admin', 'member', 'viewer'], statuses: ['active', 'disabled', 'invited'] };
let _tenantUsersLoadedFilterTenant = '';

function ensureTenantUserMetaLoaded() {
    return fetch('/api/platform/tenant-user-meta')
        .then(r => r.json())
        .then(data => {
            const roles = Array.isArray(data.roles) ? data.roles : [];
            const statuses = Array.isArray(data.statuses) ? data.statuses : [];
            if (roles.length > 0) _tenantUserMeta.roles = roles;
            if (statuses.length > 0) _tenantUserMeta.statuses = statuses;
        })
        .catch(() => {
            // Keep local defaults when backend meta is unavailable.
        });
}

function populateTenantUserRoleStatusSelects(selectedRole, selectedStatus) {
    const roleEl = document.getElementById('tenant-user-field-role');
    const statusEl = document.getElementById('tenant-user-field-status');
    if (!roleEl || !statusEl) return;
    roleEl.innerHTML = _tenantUserMeta.roles.map(role => `<option value="${escapeHtml(role)}">${escapeHtml(role)}</option>`).join('');
    statusEl.innerHTML = _tenantUserMeta.statuses.map(status => `<option value="${escapeHtml(status)}">${escapeHtml(status)}</option>`).join('');
    if (selectedRole) roleEl.value = selectedRole;
    if (!roleEl.value && _tenantUserMeta.roles[0]) roleEl.value = _tenantUserMeta.roles[0];
    if (selectedStatus) statusEl.value = selectedStatus;
    if (!statusEl.value && _tenantUserMeta.statuses[0]) statusEl.value = _tenantUserMeta.statuses[0];
}

function loadTenantSelectOptions(selectEl, selectedTenantId, includeAllOption) {
    if (!selectEl) return Promise.resolve();
    return fetch('/api/platform/tenants')
        .then(r => r.json())
        .then(data => {
            const tenants = data.tenants || [];
            const options = [];
            if (includeAllOption) {
                options.push(`<option value="">${currentLang === 'zh' ? '全部租户' : 'All tenants'}</option>`);
            }
            tenants.forEach(item => {
                const tenantId = item.tenant_id || '';
                options.push(`<option value="${escapeHtml(tenantId)}">${escapeHtml((item.name || tenantId) + ' (' + tenantId + ')')}</option>`);
            });
            selectEl.innerHTML = options.join('');
            if (selectedTenantId) selectEl.value = selectedTenantId;
            if (!selectEl.value && tenants[0]) {
                selectEl.value = includeAllOption ? '' : tenants[0].tenant_id;
            }
        })
        .catch(() => {
            if (includeAllOption) {
                selectEl.innerHTML = `<option value="">${currentLang === 'zh' ? '加载失败' : 'Failed to load'}</option>`;
            } else {
                selectEl.innerHTML = `<option value="">${t('tenant_users_no_tenants')}</option>`;
            }
        });
}

function renderTenantStatusBadge(status) {
    const normalized = String(status || '').toLowerCase();
    if (normalized === 'active') {
        return `<span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-xs font-medium bg-emerald-50 dark:bg-emerald-900/20 text-emerald-600 dark:text-emerald-300">active</span>`;
    }
    return `<span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-xs font-medium bg-slate-100 dark:bg-white/5 text-slate-500 dark:text-slate-400">${escapeHtml(normalized || '--')}</span>`;
}

function renderTenantUserStatusBadge(status) {
    const normalized = String(status || '').toLowerCase();
    if (normalized === 'active') {
        return `<span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-xs font-medium bg-emerald-50 dark:bg-emerald-900/20 text-emerald-600 dark:text-emerald-300">active</span>`;
    }
    if (normalized === 'invited') {
        return `<span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-xs font-medium bg-amber-50 dark:bg-amber-900/20 text-amber-600 dark:text-amber-300">invited</span>`;
    }
    return `<span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-xs font-medium bg-slate-100 dark:bg-white/5 text-slate-500 dark:text-slate-400">${escapeHtml(normalized || '--')}</span>`;
}

function loadTenantsView() {
    const emptyEl = document.getElementById('tenants-empty');
    const listEl = document.getElementById('tenants-list');
    fetch('/api/platform/tenants').then(r => r.json()).then(data => {
        const tenants = data.tenants || [];
        if (tenants.length === 0) {
            emptyEl.classList.remove('hidden');
            emptyEl.innerHTML = `
                <div class="w-16 h-16 rounded-2xl bg-cyan-50 dark:bg-cyan-900/20 flex items-center justify-center mb-4">
                    <i class="fas fa-building text-cyan-400 text-xl"></i>
                </div>
                <p class="text-slate-500 dark:text-slate-400 font-medium">${t('tenants_empty')}</p>
                <p class="text-sm text-slate-400 dark:text-slate-500 mt-1">${t('tenants_empty_desc')}</p>`;
            listEl.classList.add('hidden');
            return;
        }
        emptyEl.classList.add('hidden');
        listEl.classList.remove('hidden');
        listEl.innerHTML = '';
        tenants.forEach(tenant => {
            const card = document.createElement('div');
            card.className = 'bg-white dark:bg-[#1A1A1A] rounded-xl border border-slate-200 dark:border-white/10 p-5 flex flex-col gap-3 transition-all duration-200 hover:shadow-md hover:border-primary-200 dark:hover:border-primary-800';
            const statusBadge = renderTenantStatusBadge(tenant.status || 'active');
            card.innerHTML = `
                <div class="flex items-start justify-between gap-2">
                    <div class="flex items-center gap-3 min-w-0">
                        <div class="w-10 h-10 rounded-xl bg-cyan-50 dark:bg-cyan-900/20 flex items-center justify-center flex-shrink-0">
                            <i class="fas fa-building text-cyan-500 text-sm"></i>
                        </div>
                        <div class="min-w-0">
                            <div class="font-semibold text-sm text-slate-800 dark:text-slate-100 truncate">${escapeHtml(tenant.name || tenant.tenant_id)}</div>
                            <div class="text-xs text-slate-400 dark:text-slate-500 font-mono truncate">${escapeHtml(tenant.tenant_id || '--')}</div>
                        </div>
                    </div>
                    <div class="flex items-center gap-1 flex-shrink-0">
                        <button onclick="editTenant('${escapeHtml(tenant.tenant_id)}')" class="w-8 h-8 rounded-lg flex items-center justify-center text-slate-400 hover:text-primary-500 hover:bg-primary-50 dark:hover:bg-primary-900/20 transition-colors cursor-pointer" title="${t('tenants_edit')}">
                            <i class="fas fa-pen text-xs"></i>
                        </button>
                    </div>
                </div>
                <div class="flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400">
                    ${statusBadge}
                    <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-slate-100 dark:bg-white/5 font-mono">updated: ${escapeHtml(String(tenant.updated_at || '--'))}</span>
                </div>
            `;
            listEl.appendChild(card);
        });
    }).catch(() => {
        emptyEl.classList.remove('hidden');
        emptyEl.innerHTML = `
            <div class="w-16 h-16 rounded-2xl bg-red-50 dark:bg-red-900/20 flex items-center justify-center mb-4">
                <i class="fas fa-exclamation-triangle text-red-400 text-xl"></i>
            </div>
            <p class="text-slate-500 dark:text-slate-400 font-medium">${currentLang === 'zh' ? '加载失败' : 'Failed to load'}</p>`;
        listEl.classList.add('hidden');
    });
}

function openTenantModal(tenantId) {
    _tenantEditingId = tenantId || null;
    const overlay = document.getElementById('tenant-modal-overlay');
    const titleEl = document.getElementById('tenant-modal-title');
    const idField = document.getElementById('tenant-field-id');
    const nameField = document.getElementById('tenant-field-name');
    const statusField = document.getElementById('tenant-field-status');

    titleEl.textContent = _tenantEditingId ? t('tenants_edit') : t('tenants_create');
    idField.value = '';
    idField.disabled = false;
    nameField.value = '';
    statusField.value = 'active';

    if (_tenantEditingId) {
        fetch(`/api/platform/tenants/${encodeURIComponent(_tenantEditingId)}`).then(r => r.json()).then(data => {
            const tenant = data.tenant || data.data || data;
            idField.value = tenant.tenant_id || '';
            idField.disabled = true;
            nameField.value = tenant.name || '';
            statusField.value = (tenant.status || 'active').toLowerCase();
        }).catch(() => {});
    }
    overlay.classList.remove('hidden');
}

function closeTenantModal() {
    document.getElementById('tenant-modal-overlay').classList.add('hidden');
    _tenantEditingId = null;
}

function editTenant(tenantId) {
    openTenantModal(tenantId);
}

function saveTenant() {
    const idField = document.getElementById('tenant-field-id');
    const nameField = document.getElementById('tenant-field-name');
    const statusField = document.getElementById('tenant-field-status');
    const tenantId = idField.value.trim();
    const name = nameField.value.trim();
    const status = statusField.value.trim() || 'active';
    if (!tenantId && !_tenantEditingId) {
        idField.focus();
        idField.classList.add('border-red-400');
        setTimeout(() => idField.classList.remove('border-red-400'), 2000);
        return;
    }
    const body = {
        name: name || tenantId || _tenantEditingId,
        status: status,
    };
    if (!_tenantEditingId) {
        body.tenant_id = tenantId;
    }
    const url = _tenantEditingId ? `/api/platform/tenants/${encodeURIComponent(_tenantEditingId)}` : '/api/platform/tenants';
    const method = _tenantEditingId ? 'PUT' : 'POST';
    fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
    })
        .then(r => r.json())
        .then(data => {
            if (data.status === 'success' || data.tenant) {
                closeTenantModal();
                loadTenantsView();
                loadTenantUsersView();
            } else {
                alert(data.message || t('tenants_save_error'));
            }
        })
        .catch(() => alert(t('tenants_save_error')));
}

function loadTenantUsersView() {
    const filterEl = document.getElementById('tenant-users-tenant-filter');
    const emptyEl = document.getElementById('tenant-users-empty');
    const listEl = document.getElementById('tenant-users-list');
    const selectedTenant = filterEl ? (filterEl.value || '') : '';
    Promise.all([
        ensureTenantUserMetaLoaded(),
        loadTenantSelectOptions(filterEl, selectedTenant || _tenantUsersLoadedFilterTenant, true),
    ]).then(() => {
        const tenantId = filterEl ? (filterEl.value || '') : '';
        _tenantUsersLoadedFilterTenant = tenantId;
        const qs = tenantId ? `?tenant_id=${encodeURIComponent(tenantId)}` : '';
        return fetch(`/api/platform/tenant-users${qs}`);
    }).then(r => r.json()).then(data => {
        const users = data.tenant_users || [];
        if (users.length === 0) {
            emptyEl.classList.remove('hidden');
            emptyEl.innerHTML = `
                <div class="w-16 h-16 rounded-2xl bg-amber-50 dark:bg-amber-900/20 flex items-center justify-center mb-4">
                    <i class="fas fa-users text-amber-400 text-xl"></i>
                </div>
                <p class="text-slate-500 dark:text-slate-400 font-medium">${t('tenant_users_empty')}</p>
                <p class="text-sm text-slate-400 dark:text-slate-500 mt-1">${t('tenant_users_empty_desc')}</p>`;
            listEl.classList.add('hidden');
            return;
        }
        emptyEl.classList.add('hidden');
        listEl.classList.remove('hidden');
        listEl.innerHTML = '';
        users.forEach(user => {
            const card = document.createElement('div');
            card.className = 'bg-white dark:bg-[#1A1A1A] rounded-xl border border-slate-200 dark:border-white/10 p-5 flex flex-col gap-3 transition-all duration-200 hover:shadow-md hover:border-primary-200 dark:hover:border-primary-800';
            const statusBadge = renderTenantUserStatusBadge(user.status || '');
            card.innerHTML = `
                <div class="flex items-start justify-between gap-2">
                    <div class="flex items-center gap-3 min-w-0">
                        <div class="w-10 h-10 rounded-xl bg-amber-50 dark:bg-amber-900/20 flex items-center justify-center flex-shrink-0">
                            <i class="fas fa-user-shield text-amber-500 text-sm"></i>
                        </div>
                        <div class="min-w-0">
                            <div class="font-semibold text-sm text-slate-800 dark:text-slate-100 truncate">${escapeHtml(user.name || user.user_id)}</div>
                            <div class="text-xs text-slate-400 dark:text-slate-500 font-mono truncate">${escapeHtml((user.tenant_id || '--') + '/' + (user.user_id || '--'))}</div>
                        </div>
                    </div>
                    <div class="flex items-center gap-1 flex-shrink-0">
                        <button onclick="editTenantUser('${escapeHtml(user.tenant_id)}','${escapeHtml(user.user_id)}')" class="w-8 h-8 rounded-lg flex items-center justify-center text-slate-400 hover:text-primary-500 hover:bg-primary-50 dark:hover:bg-primary-900/20 transition-colors cursor-pointer" title="${t('tenant_users_edit')}">
                            <i class="fas fa-pen text-xs"></i>
                        </button>
                        <button onclick="deleteTenantUser('${escapeHtml(user.tenant_id)}','${escapeHtml(user.user_id)}')" class="w-8 h-8 rounded-lg flex items-center justify-center text-slate-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors cursor-pointer" title="${t('tenant_users_delete_title')}">
                            <i class="fas fa-trash text-xs"></i>
                        </button>
                    </div>
                </div>
                <div class="flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400">
                    ${statusBadge}
                    <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-slate-100 dark:bg-white/5 font-mono">${escapeHtml(user.role || '--')}</span>
                </div>
            `;
            listEl.appendChild(card);
        });
    }).catch(() => {
        emptyEl.classList.remove('hidden');
        emptyEl.innerHTML = `
            <div class="w-16 h-16 rounded-2xl bg-red-50 dark:bg-red-900/20 flex items-center justify-center mb-4">
                <i class="fas fa-exclamation-triangle text-red-400 text-xl"></i>
            </div>
            <p class="text-slate-500 dark:text-slate-400 font-medium">${currentLang === 'zh' ? '加载失败' : 'Failed to load'}</p>`;
        listEl.classList.add('hidden');
    });
}

function openTenantUserModal(tenantId, userId) {
    _tenantUserEditingKey = tenantId && userId ? `${tenantId}:${userId}` : null;
    const overlay = document.getElementById('tenant-user-modal-overlay');
    const titleEl = document.getElementById('tenant-user-modal-title');
    const tenantField = document.getElementById('tenant-user-field-tenant-id');
    const userIdField = document.getElementById('tenant-user-field-user-id');
    const nameField = document.getElementById('tenant-user-field-name');

    titleEl.textContent = _tenantUserEditingKey ? t('tenant_users_edit') : t('tenant_users_create');
    tenantField.value = tenantId || '';
    tenantField.disabled = false;
    userIdField.value = userId || '';
    userIdField.disabled = false;
    nameField.value = '';

    Promise.all([
        ensureTenantUserMetaLoaded(),
        loadTenantSelectOptions(tenantField, tenantId || _tenantUsersLoadedFilterTenant, false),
    ]).then(() => {
        populateTenantUserRoleStatusSelects('member', 'active');
        if (_tenantUserEditingKey) {
            tenantField.disabled = true;
            userIdField.disabled = true;
            return fetch(`/api/platform/tenant-users/${encodeURIComponent(tenantId)}/${encodeURIComponent(userId)}`)
                .then(r => r.json())
                .then(data => {
                    const user = data.tenant_user || data.data || data;
                    tenantField.value = user.tenant_id || tenantId || '';
                    userIdField.value = user.user_id || userId || '';
                    nameField.value = user.name || '';
                    populateTenantUserRoleStatusSelects(user.role || 'member', user.status || 'active');
                });
        }
        if (tenantId) tenantField.value = tenantId;
    }).catch(() => {
        alert(t('tenant_users_load_meta_error'));
    });
    overlay.classList.remove('hidden');
}

function closeTenantUserModal() {
    document.getElementById('tenant-user-modal-overlay').classList.add('hidden');
    _tenantUserEditingKey = null;
}

function editTenantUser(tenantId, userId) {
    openTenantUserModal(tenantId, userId);
}

function saveTenantUser() {
    const tenantField = document.getElementById('tenant-user-field-tenant-id');
    const userIdField = document.getElementById('tenant-user-field-user-id');
    const nameField = document.getElementById('tenant-user-field-name');
    const roleField = document.getElementById('tenant-user-field-role');
    const statusField = document.getElementById('tenant-user-field-status');

    const tenantId = tenantField.value.trim();
    const userId = userIdField.value.trim();
    const name = nameField.value.trim();
    const role = roleField.value.trim();
    const status = statusField.value.trim();

    if (!tenantId) {
        tenantField.focus();
        return;
    }
    if (!userId && !_tenantUserEditingKey) {
        userIdField.focus();
        return;
    }

    const body = {
        name: name,
        role: role,
        status: status,
    };
    let url = '';
    let method = '';
    if (_tenantUserEditingKey) {
        const [editingTenantId, editingUserId] = _tenantUserEditingKey.split(':', 2);
        url = `/api/platform/tenant-users/${encodeURIComponent(editingTenantId)}/${encodeURIComponent(editingUserId)}`;
        method = 'PUT';
    } else {
        body.tenant_id = tenantId;
        body.user_id = userId;
        url = '/api/platform/tenant-users';
        method = 'POST';
    }

    fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
    })
        .then(r => r.json())
        .then(data => {
            if (data.status === 'success' || data.tenant_user) {
                closeTenantUserModal();
                loadTenantUsersView();
            } else {
                alert(data.message || t('tenant_users_save_error'));
            }
        })
        .catch(() => alert(t('tenant_users_save_error')));
}

function deleteTenantUser(tenantId, userId) {
    showConfirmModal(t('tenant_users_delete_title'), t('tenant_users_delete_confirm'), () => {
        fetch(`/api/platform/tenant-users/${encodeURIComponent(tenantId)}/${encodeURIComponent(userId)}`, { method: 'DELETE' })
            .then(r => r.json())
            .then(data => {
                if (data.status === 'success' || data.tenant_user) {
                    loadTenantUsersView();
                } else {
                    alert(data.message || t('tenant_users_save_error'));
                }
            })
            .catch(() => alert(t('tenant_users_save_error')));
    });
}

// =====================================================================
// Bindings View
// =====================================================================
let _bindingEditingId = null;
let _bindingEditingMetadata = {};

function loadBindingsView() {
    const emptyEl = document.getElementById('bindings-empty');
    const listEl = document.getElementById('bindings-list');

    fetch('/api/platform/bindings').then(r => r.json()).then(data => {
        const bindings = data.bindings || data.data || [];
        if (bindings.length === 0) {
            emptyEl.classList.remove('hidden');
            emptyEl.innerHTML = `
                <div class="w-16 h-16 rounded-2xl bg-teal-50 dark:bg-teal-900/20 flex items-center justify-center mb-4">
                    <i class="fas fa-link text-teal-400 text-xl"></i>
                </div>
                <p class="text-slate-500 dark:text-slate-400 font-medium">${t('bindings_empty')}</p>
                <p class="text-sm text-slate-400 dark:text-slate-500 mt-1">${t('bindings_empty_desc')}</p>`;
            listEl.classList.add('hidden');
            return;
        }

        emptyEl.classList.add('hidden');
        listEl.classList.remove('hidden');
        listEl.innerHTML = '';

        bindings.forEach(binding => {
            const card = document.createElement('div');
            const metadata = binding.metadata || {};
            const enabledBadge = binding.enabled
                ? `<span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-xs font-medium bg-emerald-50 dark:bg-emerald-900/20 text-emerald-600 dark:text-emerald-300">${t('bindings_status_enabled')}</span>`
                : `<span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-xs font-medium bg-slate-100 dark:bg-white/5 text-slate-500 dark:text-slate-400">${t('bindings_status_disabled')}</span>`;
            const routeLabel = renderBindingRouteLabel(metadata, binding.enabled);

            card.className = 'bg-white dark:bg-[#1A1A1A] rounded-xl border border-slate-200 dark:border-white/10 p-5 flex flex-col gap-3 transition-all duration-200 hover:shadow-md hover:border-primary-200 dark:hover:border-primary-800';
            card.innerHTML = `
                <div class="flex items-start justify-between gap-2">
                    <div class="flex items-center gap-3 min-w-0">
                        <div class="w-10 h-10 rounded-xl bg-teal-50 dark:bg-teal-900/20 flex items-center justify-center flex-shrink-0">
                            <i class="fas fa-link text-teal-500 text-sm"></i>
                        </div>
                        <div class="min-w-0">
                            <div class="font-semibold text-sm text-slate-800 dark:text-slate-100 truncate">${escapeHtml(binding.name || binding.binding_id)}</div>
                            <div class="text-xs text-slate-400 dark:text-slate-500 font-mono truncate">${escapeHtml(binding.binding_id)}</div>
                        </div>
                    </div>
                    <div class="flex items-center gap-1 flex-shrink-0">
                        <button onclick="editBinding('${escapeHtml(binding.binding_id)}')" class="w-8 h-8 rounded-lg flex items-center justify-center text-slate-400 hover:text-primary-500 hover:bg-primary-50 dark:hover:bg-primary-900/20 transition-colors cursor-pointer" title="${t('bindings_edit')}">
                            <i class="fas fa-pen text-xs"></i>
                        </button>
                        <button onclick="deleteBinding('${escapeHtml(binding.binding_id)}')" class="w-8 h-8 rounded-lg flex items-center justify-center text-slate-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors cursor-pointer" title="${t('bindings_delete')}">
                            <i class="fas fa-trash text-xs"></i>
                        </button>
                    </div>
                </div>
                <div class="flex flex-wrap items-center gap-2 text-xs text-slate-500 dark:text-slate-400">
                    ${enabledBadge}
                    <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-slate-100 dark:bg-white/5 font-mono">${escapeHtml(binding.channel_type || '--')}</span>
                    <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-slate-100 dark:bg-white/5 font-mono">${escapeHtml(binding.tenant_id || '--')}</span>
                </div>
                <div class="text-xs text-slate-500 dark:text-slate-400">
                    <span class="font-medium text-slate-600 dark:text-slate-300">${t('bindings_field_agent')}:</span>
                    <span class="font-mono">${escapeHtml(binding.agent_id || '--')}</span>
                </div>
                <div class="text-xs text-slate-500 dark:text-slate-400">
                    <span class="font-medium text-slate-600 dark:text-slate-300">${t('bindings_route_prefix')}:</span>
                    <span>${escapeHtml(routeLabel)}</span>
                </div>
            `;
            listEl.appendChild(card);
        });
    }).catch(() => {
        emptyEl.classList.remove('hidden');
        emptyEl.innerHTML = `
            <div class="w-16 h-16 rounded-2xl bg-red-50 dark:bg-red-900/20 flex items-center justify-center mb-4">
                <i class="fas fa-exclamation-triangle text-red-400 text-xl"></i>
            </div>
            <p class="text-slate-500 dark:text-slate-400 font-medium">${currentLang === 'zh' ? '加载失败' : 'Failed to load'}</p>`;
        listEl.classList.add('hidden');
    });
}

function renderBindingRouteLabel(metadata, enabled) {
    if (!enabled) {
        return t('bindings_route_disabled');
    }
    const segments = [];
    const appId = (metadata && metadata.external_app_id) || '';
    const chatId = (metadata && metadata.external_chat_id) || '';
    const userId = (metadata && metadata.external_user_id) || '';
    if (appId) segments.push(`${t('bindings_route_app')}=${appId}`);
    if (chatId) segments.push(`${t('bindings_route_chat')}=${chatId}`);
    if (userId) segments.push(`${t('bindings_route_user')}=${userId}`);
    return segments.length > 0 ? segments.join(' · ') : t('bindings_route_any');
}

function loadBindingAgentsSelect(tenantId, selectedAgentId) {
    const selectEl = document.getElementById('binding-field-agent-id');
    selectEl.innerHTML = `<option value="">${t('bindings_loading_agents')}</option>`;
    return fetch(`/api/platform/agents?tenant_id=${encodeURIComponent(tenantId || 'default')}`)
        .then(r => r.json())
        .then(data => {
            const agents = data.agents || data.data || [];
            selectEl.innerHTML = '';
            if (agents.length === 0) {
                selectEl.innerHTML = `<option value="">${t('bindings_no_agents')}</option>`;
                return;
            }
            agents.forEach(agent => {
                const option = document.createElement('option');
                option.value = agent.agent_id;
                option.textContent = `${agent.name || agent.agent_id} (${agent.agent_id})`;
                selectEl.appendChild(option);
            });
            if (selectedAgentId) {
                selectEl.value = selectedAgentId;
            }
            if (!selectEl.value && agents[0]) {
                selectEl.value = agents[0].agent_id;
            }
        })
        .catch(() => {
            selectEl.innerHTML = `<option value="">${currentLang === 'zh' ? '加载失败' : 'Failed to load'}</option>`;
        });
}

function openBindingModal(bindingId) {
    _bindingEditingId = bindingId || null;
    _bindingEditingMetadata = {};

    const overlay = document.getElementById('binding-modal-overlay');
    const titleEl = document.getElementById('binding-modal-title');
    const tenantField = document.getElementById('binding-field-tenant-id');
    const idField = document.getElementById('binding-field-id');
    const nameField = document.getElementById('binding-field-name');
    const channelField = document.getElementById('binding-field-channel-type');
    const enabledField = document.getElementById('binding-field-enabled');
    const appField = document.getElementById('binding-field-external-app-id');
    const chatField = document.getElementById('binding-field-external-chat-id');
    const userField = document.getElementById('binding-field-external-user-id');

    titleEl.textContent = _bindingEditingId ? t('bindings_edit') : t('bindings_create');

    tenantField.value = 'default';
    tenantField.disabled = false;
    tenantField.onchange = () => loadBindingAgentsSelect(tenantField.value.trim() || 'default');
    idField.value = '';
    idField.disabled = false;
    nameField.value = '';
    channelField.value = 'web';
    enabledField.checked = true;
    appField.value = '';
    chatField.value = '';
    userField.value = '';

    if (_bindingEditingId) {
        fetch(`/api/platform/bindings/${encodeURIComponent(_bindingEditingId)}`).then(r => r.json()).then(data => {
            const binding = data.binding || data.data || data;
            const metadata = binding.metadata || {};
            _bindingEditingMetadata = Object.assign({}, metadata);
            tenantField.value = binding.tenant_id || 'default';
            tenantField.disabled = true;
            idField.value = binding.binding_id || '';
            idField.disabled = true;
            nameField.value = binding.name || '';
            channelField.value = binding.channel_type || 'web';
            enabledField.checked = !!binding.enabled;
            appField.value = metadata.external_app_id || '';
            chatField.value = metadata.external_chat_id || '';
            userField.value = metadata.external_user_id || '';
            return loadBindingAgentsSelect(tenantField.value.trim() || 'default', binding.agent_id || '');
        }).catch(() => {});
    } else {
        loadBindingAgentsSelect('default');
    }

    overlay.classList.remove('hidden');
}

function closeBindingModal() {
    document.getElementById('binding-modal-overlay').classList.add('hidden');
    _bindingEditingId = null;
    _bindingEditingMetadata = {};
}

function editBinding(bindingId) {
    openBindingModal(bindingId);
}

function deleteBinding(bindingId) {
    showConfirmModal(t('bindings_delete_title'), t('bindings_delete_confirm'), () => {
        fetch(`/api/platform/bindings/${encodeURIComponent(bindingId)}`, { method: 'DELETE' })
            .then(r => r.json())
            .then(data => {
                if (data.status === 'success' || data.binding) {
                    loadBindingsView();
                } else {
                    alert(t('bindings_save_error'));
                }
            })
            .catch(() => alert(t('bindings_save_error')));
    });
}

function collectBindingMetadata() {
    const metadata = Object.assign({}, _bindingEditingMetadata || {});
    const appId = document.getElementById('binding-field-external-app-id').value.trim();
    const chatId = document.getElementById('binding-field-external-chat-id').value.trim();
    const userId = document.getElementById('binding-field-external-user-id').value.trim();

    if (appId) metadata.external_app_id = appId;
    else delete metadata.external_app_id;
    if (chatId) metadata.external_chat_id = chatId;
    else delete metadata.external_chat_id;
    if (userId) metadata.external_user_id = userId;
    else delete metadata.external_user_id;

    return metadata;
}

function saveBinding() {
    const tenantField = document.getElementById('binding-field-tenant-id');
    const idField = document.getElementById('binding-field-id');
    const nameField = document.getElementById('binding-field-name');
    const channelField = document.getElementById('binding-field-channel-type');
    const agentField = document.getElementById('binding-field-agent-id');

    const tenantId = tenantField.value.trim() || 'default';
    const bindingId = idField.value.trim();
    const name = nameField.value.trim();
    const channelType = channelField.value.trim();
    const agentId = agentField.value.trim();

    if (!bindingId) {
        idField.focus();
        idField.classList.add('border-red-400');
        setTimeout(() => idField.classList.remove('border-red-400'), 2000);
        return;
    }
    if (!channelType) {
        channelField.focus();
        channelField.classList.add('border-red-400');
        setTimeout(() => channelField.classList.remove('border-red-400'), 2000);
        return;
    }
    if (!agentId) {
        agentField.focus();
        agentField.classList.add('border-red-400');
        setTimeout(() => agentField.classList.remove('border-red-400'), 2000);
        return;
    }

    const body = {
        tenant_id: tenantId,
        binding_id: bindingId,
        name: name || bindingId,
        channel_type: channelType,
        agent_id: agentId,
        enabled: document.getElementById('binding-field-enabled').checked,
        metadata: collectBindingMetadata(),
    };

    const isEdit = !!_bindingEditingId;
    const url = isEdit ? `/api/platform/bindings/${encodeURIComponent(_bindingEditingId)}` : '/api/platform/bindings';
    const method = isEdit ? 'PUT' : 'POST';

    fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
    })
        .then(r => r.json())
        .then(data => {
            if (data.status === 'success' || data.binding_id || data.binding) {
                closeBindingModal();
                loadBindingsView();
            } else {
                alert(data.message || t('bindings_save_error'));
            }
        })
        .catch(() => alert(t('bindings_save_error')));
}

function fetchPlatformAgentsByTenant(tenantId) {
    const normalizedTenantId = (tenantId || 'default').trim() || 'default';
    return fetch(`/api/platform/agents?tenant_id=${encodeURIComponent(normalizedTenantId)}`)
        .then(r => r.json())
        .then(data => {
            const agents = data.agents || data.data || [];
            return agents.map(agent => {
                const copy = Object.assign({}, agent);
                if (!copy.tenant_id) copy.tenant_id = normalizedTenantId;
                return copy;
            });
        });
}

function fetchAllPlatformAgents() {
    return fetch('/api/platform/tenants')
        .then(r => r.json())
        .then(data => {
            const tenants = Array.isArray(data.tenants) ? data.tenants : [];
            if (tenants.length === 0) {
                return fetchPlatformAgentsByTenant('default').catch(() => []);
            }
            const calls = tenants.map(item => fetchPlatformAgentsByTenant(item.tenant_id || 'default').catch(() => []));
            return Promise.all(calls).then(results => results.flat());
        });
}

function loadAgentsView() {
    const filterEl = document.getElementById('agents-tenant-filter');
    const emptyEl = document.getElementById('agents-empty');
    const listEl = document.getElementById('agents-list');
    const selectedTenant = filterEl ? (filterEl.value || '') : '';

    loadTenantSelectOptions(filterEl, selectedTenant || _agentsLoadedFilterTenant, true)
        .then(() => {
            const tenantId = filterEl ? (filterEl.value || '') : '';
            _agentsLoadedFilterTenant = tenantId;
            if (tenantId) {
                return fetchPlatformAgentsByTenant(tenantId);
            }
            return fetchAllPlatformAgents();
        })
        .then(agents => {
            const normalizedAgents = (agents || []).map(agent => {
                const copy = Object.assign({}, agent);
                if (!copy.tenant_id) copy.tenant_id = _agentsLoadedFilterTenant || 'default';
                return copy;
            });
            normalizedAgents.sort((left, right) => {
                const tenantCmp = String(left.tenant_id || '').localeCompare(String(right.tenant_id || ''));
                if (tenantCmp !== 0) return tenantCmp;
                return String(left.agent_id || '').localeCompare(String(right.agent_id || ''));
            });
            if (normalizedAgents.length === 0) {
                emptyEl.classList.remove('hidden');
                emptyEl.innerHTML = `
                    <div class="w-16 h-16 rounded-2xl bg-blue-50 dark:bg-blue-900/20 flex items-center justify-center mb-4">
                        <i class="fas fa-robot text-blue-400 text-xl"></i>
                    </div>
                    <p class="text-slate-500 dark:text-slate-400 font-medium">${t('agents_empty')}</p>
                    <p class="text-sm text-slate-400 dark:text-slate-500 mt-1">${t('agents_empty_desc')}</p>`;
                listEl.classList.add('hidden');
                return;
            }
            emptyEl.classList.add('hidden');
            listEl.classList.remove('hidden');
            listEl.innerHTML = '';

            normalizedAgents.forEach(agent => {
                const card = document.createElement('div');
                card.className = 'bg-white dark:bg-[#1A1A1A] rounded-xl border border-slate-200 dark:border-white/10 p-5 flex flex-col gap-3 transition-all duration-200 hover:shadow-md hover:border-primary-200 dark:hover:border-primary-800';
                const toolCount = (agent.tools || []).length;
                const skillCount = (agent.skills || []).length;
                const knowledgeLabel = agent.knowledge_enabled ? t('agents_knowledge_on') : t('agents_knowledge_off');
                const knowledgeClass = agent.knowledge_enabled ? 'text-emerald-500' : 'text-slate-400 dark:text-slate-500';
                const tenantId = String(agent.tenant_id || 'default');
                const agentId = String(agent.agent_id || '');
                card.innerHTML = `
                    <div class="flex items-start justify-between gap-2">
                        <div class="flex items-center gap-3 min-w-0">
                            <div class="w-10 h-10 rounded-xl bg-primary-50 dark:bg-primary-900/20 flex items-center justify-center flex-shrink-0">
                                <i class="fas fa-robot text-primary-500 text-sm"></i>
                            </div>
                            <div class="min-w-0">
                                <div class="font-semibold text-sm text-slate-800 dark:text-slate-100 truncate">${escapeHtml(agent.name || agentId)}</div>
                                <div class="text-xs text-slate-400 dark:text-slate-500 font-mono truncate">${escapeHtml(agentId)}</div>
                            </div>
                        </div>
                        <div class="flex items-center gap-1 flex-shrink-0">
                            <button onclick="editAgent('${escapeHtml(tenantId)}','${escapeHtml(agentId)}')" class="w-8 h-8 rounded-lg flex items-center justify-center text-slate-400 hover:text-primary-500 hover:bg-primary-50 dark:hover:bg-primary-900/20 transition-colors cursor-pointer" title="${t('agents_edit')}">
                                <i class="fas fa-pen text-xs"></i>
                            </button>
                            <button onclick="deleteAgent('${escapeHtml(tenantId)}','${escapeHtml(agentId)}')" class="w-8 h-8 rounded-lg flex items-center justify-center text-slate-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors cursor-pointer" title="${t('agents_delete')}">
                                <i class="fas fa-trash text-xs"></i>
                            </button>
                        </div>
                    </div>
                    <div class="flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400">
                        <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-slate-100 dark:bg-white/5 font-mono">${escapeHtml(tenantId)}</span>
                        <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-slate-100 dark:bg-white/5 font-mono">${escapeHtml(agent.model || '--')}</span>
                    </div>
                    <div class="flex items-center gap-3 text-xs">
                        <span class="inline-flex items-center gap-1 text-blue-500" title="${t('agents_section_tools')}">
                            <i class="fas fa-wrench text-[10px]"></i> ${toolCount} ${t('agents_tools_count')}
                        </span>
                        <span class="inline-flex items-center gap-1 text-amber-500" title="${t('agents_section_skills')}">
                            <i class="fas fa-bolt text-[10px]"></i> ${skillCount} ${t('agents_skills_count')}
                        </span>
                        <span class="inline-flex items-center gap-1 ${knowledgeClass}" title="${t('agents_section_knowledge')}">
                            <i class="fas fa-book text-[10px]"></i> ${knowledgeLabel}
                        </span>
                    </div>
                    ${agent.system_prompt ? `<p class="text-xs text-slate-400 dark:text-slate-500 line-clamp-2 mt-1">${escapeHtml(agent.system_prompt.substring(0, 120))}${agent.system_prompt.length > 120 ? '...' : ''}</p>` : ''}
                `;
                listEl.appendChild(card);
            });
        })
        .catch(() => {
            emptyEl.classList.remove('hidden');
            emptyEl.innerHTML = `
                <div class="w-16 h-16 rounded-2xl bg-red-50 dark:bg-red-900/20 flex items-center justify-center mb-4">
                    <i class="fas fa-exclamation-triangle text-red-400 text-xl"></i>
                </div>
                <p class="text-slate-500 dark:text-slate-400 font-medium">${currentLang === 'zh' ? '加载失败' : 'Failed to load'}</p>`;
            listEl.classList.add('hidden');
        });
}

function openAgentModal(agentId, tenantId) {
    _agentEditingId = agentId || null;
    _agentEditingTenantId = tenantId || null;
    const overlay = document.getElementById('agent-modal-overlay');
    const titleEl = document.getElementById('agent-modal-title');
    const tenantField = document.getElementById('agent-field-tenant-id');
    const idField = document.getElementById('agent-field-id');
    const nameField = document.getElementById('agent-field-name');
    const modelField = document.getElementById('agent-field-model');
    const promptField = document.getElementById('agent-field-prompt');
    const knowledgeField = document.getElementById('agent-field-knowledge');

    titleEl.textContent = _agentEditingId ? t('agents_edit') : t('agents_create');

    // Reset fields
    tenantField.value = _agentEditingTenantId || _agentsLoadedFilterTenant || 'default';
    tenantField.disabled = false;
    idField.value = '';
    idField.disabled = false;
    idField.placeholder = currentLang === 'zh' ? '留空自动生成' : 'Leave empty for auto-generated id';
    nameField.value = '';
    promptField.value = '';
    knowledgeField.checked = false;
    document.getElementById('agent-mcp-servers').innerHTML = '';

    // Populate model select
    modelField.innerHTML = AVAILABLE_MODELS.map(m => `<option value="${m}">${m}</option>`).join('');

    // Load tools & skills checkboxes
    loadAgentToolsCheckboxes([]);
    loadAgentSkillsCheckboxes([]);

    if (_agentEditingId) {
        loadTenantSelectOptions(tenantField, tenantField.value || 'default', false)
            .then(() => {
                const resolvedTenantId = (String(_agentEditingTenantId || tenantField.value || 'default').trim() || 'default');
                _agentEditingTenantId = resolvedTenantId;
                tenantField.value = resolvedTenantId;
                tenantField.disabled = true;
                return fetch(`/api/platform/agents/${encodeURIComponent(_agentEditingId)}?tenant_id=${encodeURIComponent(resolvedTenantId)}`);
            })
            .then(r => r.json())
            .then(data => {
                const agent = data.agent || data.data || data;
                idField.value = agent.agent_id || '';
                idField.disabled = true;
                if (agent.tenant_id) {
                    tenantField.value = agent.tenant_id;
                    _agentEditingTenantId = agent.tenant_id;
                }
                nameField.value = agent.name || '';
                promptField.value = agent.system_prompt || '';
                knowledgeField.checked = !!agent.knowledge_enabled;

                // Set model
                if (agent.model) {
                    const opts = Array.from(modelField.options).map(o => o.value);
                    if (!opts.includes(agent.model)) {
                        modelField.innerHTML += `<option value="${escapeHtml(agent.model)}">${escapeHtml(agent.model)}</option>`;
                    }
                    modelField.value = agent.model;
                }

                // Set tools
                loadAgentToolsCheckboxes(agent.tools || []);
                // Set skills
                loadAgentSkillsCheckboxes(agent.skills || []);

                // Set MCP servers
                renderMcpServers(agent.mcp_servers || {});
            })
            .catch(() => {});
    } else {
        loadTenantSelectOptions(tenantField, tenantField.value || 'default', false).then(() => {
            if (!tenantField.value) tenantField.value = 'default';
        });
    }

    overlay.classList.remove('hidden');
}

function closeAgentModal() {
    document.getElementById('agent-modal-overlay').classList.add('hidden');
    _agentEditingId = null;
    _agentEditingTenantId = null;
}

function editAgent(tenantId, agentId) {
    openAgentModal(agentId, tenantId);
}

function deleteAgent(tenantId, agentId) {
    const resolvedTenantId = String(tenantId || 'default').trim() || 'default';
    showConfirmModal(t('agents_delete_title'), t('agents_delete_confirm'), () => {
        fetch(`/api/platform/agents/${encodeURIComponent(agentId)}?tenant_id=${encodeURIComponent(resolvedTenantId)}`, { method: 'DELETE' })
            .then(r => r.json())
            .then(data => {
                if (data.status === 'success' || data.agent_id) {
                    loadAgentsView();
                } else {
                    alert(t('agents_save_error'));
                }
            })
            .catch(() => alert(t('agents_save_error')));
    });
}

function loadAgentToolsCheckboxes(selectedTools) {
    const container = document.getElementById('agent-tools-checkboxes');
    container.innerHTML = `<div class="col-span-2 text-xs text-slate-400 dark:text-slate-500"><i class="fas fa-spinner fa-spin mr-1"></i>${t('agents_loading_tools')}</div>`;

    fetch('/api/tools').then(r => r.json()).then(data => {
        const tools = data.tools || [];
        _agentToolsCache = tools;
        if (tools.length === 0) {
            container.innerHTML = `<div class="col-span-2 text-xs text-slate-400 dark:text-slate-500">${currentLang === 'zh' ? '暂无可用工具' : 'No tools available'}</div>`;
            return;
        }
        container.innerHTML = '';
        tools.forEach(tool => {
            const checked = selectedTools.includes(tool.name);
            const label = document.createElement('label');
            label.className = 'flex items-center gap-2 px-2 py-1.5 rounded-md hover:bg-slate-100 dark:hover:bg-white/5 cursor-pointer text-xs text-slate-700 dark:text-slate-300';
            label.innerHTML = `
                <input type="checkbox" name="agent-tool" value="${escapeHtml(tool.name)}" ${checked ? 'checked' : ''} class="rounded border-slate-300 dark:border-slate-600 text-primary-500 focus:ring-primary-500/20">
                <span class="truncate">${escapeHtml(tool.name)}</span>`;
            container.appendChild(label);
        });
    }).catch(() => {
        container.innerHTML = `<div class="col-span-2 text-xs text-red-400">${currentLang === 'zh' ? '加载失败' : 'Failed to load'}</div>`;
    });
}

function loadAgentSkillsCheckboxes(selectedSkills) {
    const container = document.getElementById('agent-skills-checkboxes');
    container.innerHTML = `<div class="col-span-2 text-xs text-slate-400 dark:text-slate-500"><i class="fas fa-spinner fa-spin mr-1"></i>${t('agents_loading_skills')}</div>`;

    fetch(appendAgentQuery('/api/skills')).then(r => r.json()).then(data => {
        const skills = data.skills || [];
        _agentSkillsCache = skills;
        if (skills.length === 0) {
            container.innerHTML = `<div class="col-span-2 text-xs text-slate-400 dark:text-slate-500">${currentLang === 'zh' ? '暂无可用技能' : 'No skills available'}</div>`;
            return;
        }
        container.innerHTML = '';
        skills.forEach(sk => {
            const checked = selectedSkills.includes(sk.name);
            const label = document.createElement('label');
            label.className = 'flex items-center gap-2 px-2 py-1.5 rounded-md hover:bg-slate-100 dark:hover:bg-white/5 cursor-pointer text-xs text-slate-700 dark:text-slate-300';
            label.innerHTML = `
                <input type="checkbox" name="agent-skill" value="${escapeHtml(sk.name)}" ${checked ? 'checked' : ''} class="rounded border-slate-300 dark:border-slate-600 text-primary-500 focus:ring-primary-500/20">
                <span class="truncate">${escapeHtml(sk.display_name || sk.name)}</span>`;
            container.appendChild(label);
        });
    }).catch(() => {
        container.innerHTML = `<div class="col-span-2 text-xs text-red-400">${currentLang === 'zh' ? '加载失败' : 'Failed to load'}</div>`;
    });
}

function renderMcpServers(mcpServers) {
    const container = document.getElementById('agent-mcp-servers');
    container.innerHTML = '';
    if (!mcpServers || typeof mcpServers !== 'object') return;

    Object.entries(mcpServers).forEach(([name, config]) => {
        const cmd = (config && config.command) || '';
        const args = Array.isArray(config && config.args) ? config.args.join(', ') : '';
        addMcpServerRow(name, cmd, args);
    });
}

function addMcpServerRow(name, command, args) {
    const container = document.getElementById('agent-mcp-servers');
    const row = document.createElement('div');
    row.className = 'flex items-center gap-2 p-2 rounded-lg border border-slate-100 dark:border-white/5 bg-slate-50 dark:bg-white/[0.02]';
    row.innerHTML = `
        <input type="text" placeholder="${t('agents_mcp_name')}" value="${escapeHtml(name || '')}" class="agent-mcp-name flex-1 min-w-0 px-2 py-1 rounded border border-slate-200 dark:border-white/10 bg-white dark:bg-white/5 text-xs text-slate-700 dark:text-slate-200 focus:outline-none focus:border-primary-500">
        <input type="text" placeholder="${t('agents_mcp_command')}" value="${escapeHtml(command || '')}" class="agent-mcp-command flex-1 min-w-0 px-2 py-1 rounded border border-slate-200 dark:border-white/10 bg-white dark:bg-white/5 text-xs text-slate-700 dark:text-slate-200 focus:outline-none focus:border-primary-500">
        <input type="text" placeholder="${t('agents_mcp_args')}" value="${escapeHtml(args || '')}" class="agent-mcp-args flex-1 min-w-0 px-2 py-1 rounded border border-slate-200 dark:border-white/10 bg-white dark:bg-white/5 text-xs text-slate-700 dark:text-slate-200 focus:outline-none focus:border-primary-500">
        <button type="button" onclick="this.parentElement.remove()" class="w-6 h-6 rounded flex items-center justify-center text-slate-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors cursor-pointer flex-shrink-0">
            <i class="fas fa-xmark text-xs"></i>
        </button>`;
    container.appendChild(row);
}

function collectMcpServers() {
    const rows = document.querySelectorAll('#agent-mcp-servers > div');
    const result = {};
    rows.forEach(row => {
        const name = row.querySelector('.agent-mcp-name')?.value?.trim();
        const command = row.querySelector('.agent-mcp-command')?.value?.trim();
        const argsStr = row.querySelector('.agent-mcp-args')?.value?.trim();
        if (!name) return;
        const entry = {};
        if (command) entry.command = command;
        if (argsStr) entry.args = argsStr.split(',').map(s => s.trim()).filter(Boolean);
        result[name] = entry;
    });
    return result;
}

function saveAgent() {
    const tenantField = document.getElementById('agent-field-tenant-id');
    const idField = document.getElementById('agent-field-id');
    const inputAgentId = idField.value.trim();
    const selectedTenantId = (tenantField?.value || '').trim();
    const name = document.getElementById('agent-field-name').value.trim();
    const model = document.getElementById('agent-field-model').value;
    const systemPrompt = document.getElementById('agent-field-prompt').value;
    const knowledgeEnabled = document.getElementById('agent-field-knowledge').checked;
    const isEdit = !!_agentEditingId;
    const resolvedAgentId = isEdit ? (_agentEditingId || '') : inputAgentId;
    const resolvedTenantId = (isEdit ? (_agentEditingTenantId || selectedTenantId) : selectedTenantId) || 'default';

    if (isEdit && !resolvedAgentId) {
        alert(t('agents_save_error'));
        return;
    }

    // Collect tools
    const tools = Array.from(document.querySelectorAll('input[name="agent-tool"]:checked')).map(cb => cb.value);
    // Collect skills
    const skills = Array.from(document.querySelectorAll('input[name="agent-skill"]:checked')).map(cb => cb.value);
    // Collect MCP servers
    const mcpServers = collectMcpServers();
    const fallbackName = currentLang === 'zh' ? '新智能体' : 'New Agent';

    const body = {
        tenant_id: resolvedTenantId,
        name: name || resolvedAgentId || fallbackName,
        model: model,
        system_prompt: systemPrompt,
        tools: tools,
        skills: skills,
        knowledge_enabled: knowledgeEnabled,
        mcp_servers: mcpServers
    };
    if (!isEdit && resolvedAgentId) {
        body.agent_id = resolvedAgentId;
    }

    const url = isEdit ? `/api/platform/agents/${encodeURIComponent(_agentEditingId)}` : '/api/platform/agents';
    const method = isEdit ? 'PUT' : 'POST';

    fetch(url, {
        method: method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
    })
    .then(r => r.json())
    .then(data => {
        if (data.status === 'success' || data.agent_id) {
            closeAgentModal();
            loadAgentsView();
        } else {
            alert(data.message || t('agents_save_error'));
        }
    })
    .catch(() => alert(t('agents_save_error')));
}

// =====================================================================
// MCP View
// =====================================================================
let _mcpEditingName = null;  // null = create mode, string = edit mode
let _mcpAgentsCache = [];    // cached agents list for the selector
let _mcpSelectedAgentId = null;

function loadMcpView() {
    const emptyEl = document.getElementById('mcp-empty');
    const listEl = document.getElementById('mcp-list');
    const selectEl = document.getElementById('mcp-agent-select');

    // First, load agents for the selector if not cached
    const loadServers = (agentId) => {
        let url = '/api/mcp/servers';
        if (agentId) {
            url += `?agent_id=${encodeURIComponent(agentId)}`;
        } else if (currentAgentId) {
            url += `?agent_id=${encodeURIComponent(currentAgentId)}`;
        }

        fetch(url).then(r => r.json()).then(data => {
            if (data.status !== 'success') {
                emptyEl.classList.remove('hidden');
                emptyEl.innerHTML = `
                    <div class="w-16 h-16 rounded-2xl bg-red-50 dark:bg-red-900/20 flex items-center justify-center mb-4">
                        <i class="fas fa-exclamation-triangle text-red-400 text-xl"></i>
                    </div>
                    <p class="text-slate-500 dark:text-slate-400 font-medium">${currentLang === 'zh' ? '加载失败' : 'Failed to load'}</p>`;
                listEl.classList.add('hidden');
                return;
            }

            const servers = data.servers || [];
            if (servers.length === 0) {
                emptyEl.classList.remove('hidden');
                emptyEl.innerHTML = `
                    <div class="w-16 h-16 rounded-2xl bg-violet-50 dark:bg-violet-900/20 flex items-center justify-center mb-4">
                        <i class="fas fa-plug text-violet-400 text-xl"></i>
                    </div>
                    <p class="text-slate-500 dark:text-slate-400 font-medium">${t('mcp_no_servers')}</p>
                    <p class="text-sm text-slate-400 dark:text-slate-500 mt-1">${t('mcp_no_servers_desc')}</p>`;
                listEl.classList.add('hidden');
                return;
            }

            emptyEl.classList.add('hidden');
            listEl.classList.remove('hidden');
            listEl.innerHTML = '';

            servers.forEach(server => {
                const card = document.createElement('div');
                card.className = 'mcp-server-card bg-white dark:bg-[#1A1A1A] rounded-xl border border-slate-200 dark:border-white/10 p-5 flex flex-col gap-3 transition-all duration-200 hover:shadow-md hover:border-primary-200 dark:hover:border-primary-800';
                const argsStr = Array.isArray(server.args) ? server.args.join(' ') : '';
                const envCount = server.env ? Object.keys(server.env).length : 0;
                card.innerHTML = `
                    <div class="flex items-start justify-between gap-2">
                        <div class="flex items-center gap-3 min-w-0">
                            <div class="w-10 h-10 rounded-xl bg-violet-50 dark:bg-violet-900/20 flex items-center justify-center flex-shrink-0">
                                <i class="fas fa-plug text-violet-500 text-sm"></i>
                            </div>
                            <div class="min-w-0">
                                <div class="font-semibold text-sm text-slate-800 dark:text-slate-100 truncate">${escapeHtml(server.name)}</div>
                                <div class="text-xs text-slate-400 dark:text-slate-500 font-mono truncate mt-0.5">${escapeHtml(server.command)} ${escapeHtml(argsStr)}</div>
                            </div>
                        </div>
                        <div class="flex items-center gap-1 flex-shrink-0">
                            <button onclick="editMcpServer('${escapeHtml(server.name)}')" class="w-8 h-8 rounded-lg flex items-center justify-center text-slate-400 hover:text-primary-500 hover:bg-primary-50 dark:hover:bg-primary-900/20 transition-colors cursor-pointer" title="${t('mcp_edit')}">
                                <i class="fas fa-pen text-xs"></i>
                            </button>
                            <button onclick="deleteMcpServer('${escapeHtml(server.name)}')" class="w-8 h-8 rounded-lg flex items-center justify-center text-slate-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors cursor-pointer" title="${t('mcp_delete')}">
                                <i class="fas fa-trash text-xs"></i>
                            </button>
                        </div>
                    </div>
                    <div class="flex items-center gap-3 text-xs">
                        ${envCount > 0 ? `<span class="inline-flex items-center gap-1 text-slate-500 dark:text-slate-400" title="${t('mcp_env')}"><i class="fas fa-key text-[10px]"></i> ${envCount} ${currentLang === 'zh' ? '个变量' : 'vars'}</span>` : ''}
                    </div>
                    <!-- Tools collapsible -->
                    <div class="mcp-tools-section">
                        <button onclick="toggleMcpTools(this, '${escapeHtml(server.name)}')" class="inline-flex items-center gap-1.5 text-xs font-medium text-primary-500 hover:text-primary-600 cursor-pointer transition-colors">
                            <i class="fas fa-chevron-right text-[10px] mcp-tools-chevron transition-transform duration-200"></i>
                            <span class="mcp-tools-toggle-text">${t('mcp_view_tools')}</span>
                        </button>
                        <div class="mcp-tools-list hidden mt-2 pl-4 space-y-1"></div>
                    </div>
                `;
                listEl.appendChild(card);
            });
        }).catch(() => {
            emptyEl.classList.remove('hidden');
            emptyEl.innerHTML = `
                <div class="w-16 h-16 rounded-2xl bg-red-50 dark:bg-red-900/20 flex items-center justify-center mb-4">
                    <i class="fas fa-exclamation-triangle text-red-400 text-xl"></i>
                </div>
                <p class="text-slate-500 dark:text-slate-400 font-medium">${currentLang === 'zh' ? '加载失败' : 'Failed to load'}</p>`;
            listEl.classList.add('hidden');
        });
    };

    // Load agents for the selector
    fetch('/api/platform/agents').then(r => r.json()).then(data => {
        const agents = data.agents || data.data || [];
        _mcpAgentsCache = agents;
        selectEl.innerHTML = '';
        if (agents.length === 0) {
            selectEl.innerHTML = `<option value="">${currentLang === 'zh' ? '暂无智能体' : 'No agents'}</option>`;
        } else {
            agents.forEach(agent => {
                const opt = document.createElement('option');
                opt.value = agent.agent_id;
                opt.textContent = agent.name || agent.agent_id;
                selectEl.appendChild(opt);
            });
        }
        // Set selected agent
        const targetId = _mcpSelectedAgentId || currentAgentId;
        if (targetId) {
            selectEl.value = targetId;
        }
        _mcpSelectedAgentId = selectEl.value;

        // Load servers for selected agent
        loadServers(_mcpSelectedAgentId);
    }).catch(() => {
        selectEl.innerHTML = `<option value="">${currentLang === 'zh' ? '加载失败' : 'Failed to load'}</option>`;
        loadServers(null);
    });

    // Update selected agent on change
    selectEl.onchange = () => {
        _mcpSelectedAgentId = selectEl.value;
        loadServers(_mcpSelectedAgentId);
    };
}

function toggleMcpTools(btn, serverName) {
    const section = btn.closest('.mcp-tools-section');
    const toolsList = section.querySelector('.mcp-tools-list');
    const chevron = btn.querySelector('.mcp-tools-chevron');
    const toggleText = btn.querySelector('.mcp-tools-toggle-text');

    if (!toolsList.classList.contains('hidden')) {
        toolsList.classList.add('hidden');
        chevron.style.transform = '';
        toggleText.textContent = t('mcp_view_tools');
        return;
    }

    // Load tools if not yet loaded
    if (toolsList.dataset.loaded === 'true') {
        toolsList.classList.remove('hidden');
        chevron.style.transform = 'rotate(90deg)';
        toggleText.textContent = t('mcp_hide_tools');
        return;
    }

    toolsList.innerHTML = `<div class="text-xs text-slate-400 dark:text-slate-500"><i class="fas fa-spinner fa-spin mr-1"></i>${currentLang === 'zh' ? '加载工具中...' : 'Loading tools...'}</div>`;
    toolsList.classList.remove('hidden');
    chevron.style.transform = 'rotate(90deg)';
    toggleText.textContent = t('mcp_hide_tools');

    const agentId = _mcpSelectedAgentId || currentAgentId || '';
    let url = `/api/mcp/servers/${encodeURIComponent(serverName)}/tools`;
    if (agentId) {
        url += `?agent_id=${encodeURIComponent(agentId)}`;
    }

    fetch(url).then(r => r.json()).then(data => {
        if (data.status !== 'success') {
            toolsList.innerHTML = `<div class="text-xs text-red-400">${escapeHtml(data.message || t('mcp_no_tools'))}</div>`;
            return;
        }
        const tools = data.tools || [];
        if (tools.length === 0) {
            toolsList.innerHTML = `<div class="text-xs text-slate-400 dark:text-slate-500">${t('mcp_no_tools')}</div>`;
        } else {
            toolsList.innerHTML = tools.map(tool => `
                <div class="flex items-start gap-2 p-2 rounded-md bg-slate-50 dark:bg-white/[0.02] border border-slate-100 dark:border-white/5">
                    <i class="fas fa-wrench text-[10px] text-slate-400 mt-0.5 flex-shrink-0"></i>
                    <div class="min-w-0">
                        <div class="text-xs font-medium text-slate-700 dark:text-slate-200 font-mono">${escapeHtml(tool.name)}</div>
                        ${tool.description ? `<div class="text-xs text-slate-400 dark:text-slate-500 mt-0.5 line-clamp-2">${escapeHtml(tool.description)}</div>` : ''}
                    </div>
                </div>
            `).join('');
        }
        toolsList.dataset.loaded = 'true';
    }).catch(() => {
        toolsList.innerHTML = `<div class="text-xs text-red-400">${currentLang === 'zh' ? '加载失败' : 'Failed to load'}</div>`;
    });
}

function openMcpServerModal(existingName) {
    _mcpEditingName = existingName || null;
    const overlay = document.getElementById('mcp-modal-overlay');
    const titleEl = document.getElementById('mcp-modal-title');
    const nameField = document.getElementById('mcp-field-name');
    const commandField = document.getElementById('mcp-field-command');
    const argsField = document.getElementById('mcp-field-args');
    const envRows = document.getElementById('mcp-env-rows');
    const testResult = document.getElementById('mcp-test-result');

    titleEl.textContent = _mcpEditingName ? t('mcp_edit_server') : t('mcp_add_server');
    nameField.value = '';
    nameField.disabled = false;
    commandField.value = '';
    argsField.value = '';
    envRows.innerHTML = '';
    testResult.classList.add('hidden');

    if (_mcpEditingName) {
        // Load current server config
        const agentId = _mcpSelectedAgentId || currentAgentId || '';
        let url = '/api/mcp/servers';
        if (agentId) {
            url += `?agent_id=${encodeURIComponent(agentId)}`;
        }
        fetch(url).then(r => r.json()).then(data => {
            if (data.status !== 'success') return;
            const server = (data.servers || []).find(s => s.name === _mcpEditingName);
            if (!server) return;
            nameField.value = server.name || '';
            nameField.disabled = true;  // Don't allow renaming
            commandField.value = server.command || '';
            argsField.value = Array.isArray(server.args) ? server.args.join(' ') : '';
            // Populate env vars
            if (server.env && typeof server.env === 'object') {
                Object.entries(server.env).forEach(([key, val]) => {
                    addMcpEnvRow(key, val);
                });
            }
        }).catch(() => {});
    }

    overlay.classList.remove('hidden');
}

function closeMcpServerModal() {
    document.getElementById('mcp-modal-overlay').classList.add('hidden');
    _mcpEditingName = null;
}

function editMcpServer(name) {
    openMcpServerModal(name);
}

function addMcpEnvRow(key, value) {
    const container = document.getElementById('mcp-env-rows');
    const row = document.createElement('div');
    row.className = 'flex items-center gap-2';
    row.innerHTML = `
        <input type="text" placeholder="${t('mcp_env_key')}" value="${escapeHtml(key || '')}" class="mcp-env-key flex-1 min-w-0 px-2 py-1 rounded border border-slate-200 dark:border-white/10 bg-white dark:bg-white/5 text-xs text-slate-700 dark:text-slate-200 focus:outline-none focus:border-primary-500">
        <input type="text" placeholder="${t('mcp_env_value')}" value="${escapeHtml(value || '')}" class="mcp-env-value flex-1 min-w-0 px-2 py-1 rounded border border-slate-200 dark:border-white/10 bg-white dark:bg-white/5 text-xs text-slate-700 dark:text-slate-200 focus:outline-none focus:border-primary-500">
        <button type="button" onclick="this.parentElement.remove()" class="w-6 h-6 rounded flex items-center justify-center text-slate-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors cursor-pointer flex-shrink-0">
            <i class="fas fa-xmark text-xs"></i>
        </button>`;
    container.appendChild(row);
}

function collectMcpEnvFromModal() {
    const rows = document.querySelectorAll('#mcp-env-rows > div');
    const result = {};
    rows.forEach(row => {
        const key = row.querySelector('.mcp-env-key')?.value?.trim();
        const value = row.querySelector('.mcp-env-value')?.value?.trim();
        if (key) result[key] = value || '';
    });
    return result;
}

function testMcpConnection() {
    const command = document.getElementById('mcp-field-command').value.trim();
    const argsStr = document.getElementById('mcp-field-args').value.trim();
    const env = collectMcpEnvFromModal();
    const testBtn = document.getElementById('mcp-test-btn');
    const testResult = document.getElementById('mcp-test-result');

    if (!command) {
        testResult.classList.remove('hidden');
        testResult.innerHTML = `<div class="p-3 rounded-lg border text-xs"><i class="fas fa-circle-exclamation text-amber-500 mr-1"></i>${t('mcp_command_required')}</div>`;
        return;
    }

    // Parse args (space-separated, but respect quoted strings)
    const args = argsStr ? argsStr.match(/(?:"[^"]*"|'[^']*'|\S+)/g)?.map(s => s.replace(/^['"]|['"]$/g, '')) || [] : [];

    // Show loading state
    testBtn.disabled = true;
    testBtn.innerHTML = `<i class="fas fa-spinner fa-spin text-xs"></i><span>${t('mcp_test_testing')}</span>`;
    testResult.classList.remove('hidden');
    testResult.innerHTML = `<div class="p-3 rounded-lg border text-xs text-slate-500"><i class="fas fa-spinner fa-spin mr-1"></i>${t('mcp_test_testing')}</div>`;

    fetch('/api/mcp/servers/test', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ command, args, env: Object.keys(env).length > 0 ? env : null })
    })
    .then(r => r.json())
    .then(data => {
        testBtn.disabled = false;
        testBtn.innerHTML = `<i class="fas fa-plug text-xs"></i><span>${t('mcp_test_connection')}</span>`;

        if (data.status === 'success') {
            const tools = data.tools || [];
            const toolsListHtml = tools.length > 0
                ? `<div class="mt-2 space-y-1">${tools.map(t => `<div class="flex items-center gap-1.5"><i class="fas fa-wrench text-[9px] text-primary-400"></i><span class="font-mono text-xs">${escapeHtml(t.name || t)}</span></div>`).join('')}</div>`
                : '';
            testResult.innerHTML = `
                <div class="p-3 rounded-lg border border-emerald-200 dark:border-emerald-800 bg-emerald-50 dark:bg-emerald-900/20 text-xs">
                    <div class="flex items-center gap-1.5 text-emerald-600 dark:text-emerald-400 font-medium">
                        <i class="fas fa-circle-check text-sm"></i>
                        ${t('mcp_test_success')}
                    </div>
                    <div class="text-emerald-500 dark:text-emerald-400/80 mt-1">${t('mcp_tools_found').replace('{n}', tools.length)}</div>
                    ${toolsListHtml}
                </div>`;
        } else {
            testResult.innerHTML = `
                <div class="p-3 rounded-lg border border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-900/20 text-xs">
                    <div class="flex items-center gap-1.5 text-red-600 dark:text-red-400 font-medium">
                        <i class="fas fa-circle-xmark text-sm"></i>
                        ${t('mcp_test_failed')}
                    </div>
                    <div class="text-red-500 dark:text-red-400/80 mt-1 break-all">${escapeHtml(data.message || '')}</div>
                </div>`;
        }
    })
    .catch(() => {
        testBtn.disabled = false;
        testBtn.innerHTML = `<i class="fas fa-plug text-xs"></i><span>${t('mcp_test_connection')}</span>`;
        testResult.innerHTML = `
            <div class="p-3 rounded-lg border border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-900/20 text-xs">
                <div class="flex items-center gap-1.5 text-red-600 dark:text-red-400 font-medium">
                    <i class="fas fa-circle-xmark text-sm"></i>
                    ${t('mcp_test_failed')}
                </div>
            </div>`;
    });
}

function saveMcpServer() {
    const name = document.getElementById('mcp-field-name').value.trim();
    const command = document.getElementById('mcp-field-command').value.trim();
    const argsStr = document.getElementById('mcp-field-args').value.trim();
    const env = collectMcpEnvFromModal();

    // Validate
    const nameField = document.getElementById('mcp-field-name');
    const commandField = document.getElementById('mcp-field-command');
    if (!name) {
        nameField.focus();
        nameField.classList.add('border-red-400');
        setTimeout(() => nameField.classList.remove('border-red-400'), 2000);
        return;
    }
    if (!command) {
        commandField.focus();
        commandField.classList.add('border-red-400');
        setTimeout(() => commandField.classList.remove('border-red-400'), 2000);
        return;
    }

    const args = argsStr ? argsStr.match(/(?:"[^"]*"|'[^']*'|\S+)/g)?.map(s => s.replace(/^['"]|['"]$/g, '')) || [] : [];

    // Build the server entry
    const serverEntry = { command, args };
    if (Object.keys(env).length > 0) {
        serverEntry.env = env;
    }

    // Get the current agent's mcp_servers and update it
    const agentId = _mcpSelectedAgentId || currentAgentId;
    if (!agentId) {
        alert(currentLang === 'zh' ? '请先选择一个智能体' : 'Please select an agent first');
        return;
    }

    // Fetch current agent config, update mcp_servers, and save back
    fetch(`/api/platform/agents/${encodeURIComponent(agentId)}`).then(r => r.json()).then(data => {
        const agent = data.agent || data.data || data;
        const mcpServers = Object.assign({}, agent.mcp_servers || {});
        mcpServers[name] = serverEntry;

        const body = {
            agent_id: agent.agent_id,
            name: agent.name || agent.agent_id,
            model: agent.model || '',
            system_prompt: agent.system_prompt || '',
            tools: agent.tools || [],
            skills: agent.skills || [],
            knowledge_enabled: !!agent.knowledge_enabled,
            mcp_servers: mcpServers
        };

        return fetch(`/api/platform/agents/${encodeURIComponent(agentId)}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });
    })
    .then(r => r && r.json())
    .then(data => {
        if (data && (data.status === 'success' || data.agent_id)) {
            closeMcpServerModal();
            loadMcpView();
        } else {
            alert((data && data.message) || t('mcp_save_error'));
        }
    })
    .catch(() => alert(t('mcp_save_error')));
}

function deleteMcpServer(serverName) {
    showConfirmModal(t('mcp_delete_title'), t('mcp_delete_confirm'), () => {
        const agentId = _mcpSelectedAgentId || currentAgentId;
        if (!agentId) return;

        fetch(`/api/platform/agents/${encodeURIComponent(agentId)}`).then(r => r.json()).then(data => {
            const agent = data.agent || data.data || data;
            const mcpServers = Object.assign({}, agent.mcp_servers || {});
            delete mcpServers[serverName];

            const body = {
                agent_id: agent.agent_id,
                name: agent.name || agent.agent_id,
                model: agent.model || '',
                system_prompt: agent.system_prompt || '',
                tools: agent.tools || [],
                skills: agent.skills || [],
                knowledge_enabled: !!agent.knowledge_enabled,
                mcp_servers: mcpServers
            };

            return fetch(`/api/platform/agents/${encodeURIComponent(agentId)}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body)
            });
        })
        .then(r => r && r.json())
        .then(data => {
            if (data && (data.status === 'success' || data.agent_id)) {
                loadMcpView();
            } else {
                alert(t('mcp_save_error'));
            }
        })
        .catch(() => alert(t('mcp_save_error')));
    });
}

// =====================================================================
// Memory View
// =====================================================================
let memoryPage = 1;
let memoryCategory = 'memory';   // 'memory' | 'dream'
const memoryPageSize = 10;

function switchMemoryTab(tab) {
    document.querySelectorAll('.memory-tab').forEach(el => el.classList.remove('active'));
    document.getElementById('memory-tab-' + tab).classList.add('active');
    memoryCategory = tab === 'dreams' ? 'dream' : 'memory';
    loadMemoryView(1);
}

function loadMemoryView(page) {
    page = page || 1;
    memoryPage = page;
    fetch(appendAgentQuery(`/api/memory?page=${page}&page_size=${memoryPageSize}&category=${memoryCategory}`)).then(r => r.json()).then(data => {
        if (data.status !== 'success') return;
        const emptyEl = document.getElementById('memory-empty');
        const listEl = document.getElementById('memory-list');
        const files = data.list || [];
        const total = data.total || 0;

        if (total === 0) {
            const emptyIcon = emptyEl.querySelector('i');
            const emptyTitle = emptyEl.querySelector('p');
            if (memoryCategory === 'dream') {
                emptyIcon.className = 'fas fa-moon text-purple-400 text-xl';
                emptyTitle.textContent = currentLang === 'zh' ? '暂无梦境日记' : 'No dream diaries yet';
            } else {
                emptyIcon.className = 'fas fa-brain text-purple-400 text-xl';
                emptyTitle.textContent = currentLang === 'zh' ? '暂无记忆文件' : 'No memory files';
            }
            emptyEl.classList.remove('hidden');
            listEl.classList.add('hidden');
            return;
        }
        emptyEl.classList.add('hidden');
        listEl.classList.remove('hidden');

        const tbody = document.getElementById('memory-table-body');
        tbody.innerHTML = '';
        files.forEach(f => {
            const tr = document.createElement('tr');
            tr.className = 'border-b border-slate-100 dark:border-white/5 hover:bg-slate-50 dark:hover:bg-white/5 cursor-pointer transition-colors';
            tr.onclick = () => openMemoryFile(f.filename, memoryCategory);
            let typeLabel;
            if (f.type === 'global') {
                typeLabel = '<span class="px-2 py-0.5 rounded-full text-xs bg-primary-50 dark:bg-primary-900/30 text-primary-600 dark:text-primary-400">Global</span>';
            } else if (f.type === 'dream') {
                typeLabel = '<span class="px-2 py-0.5 rounded-full text-xs bg-violet-50 dark:bg-violet-900/30 text-violet-600 dark:text-violet-400">Dream</span>';
            } else {
                typeLabel = '<span class="px-2 py-0.5 rounded-full text-xs bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400">Daily</span>';
            }
            const sizeStr = f.size < 1024 ? f.size + ' B' : (f.size / 1024).toFixed(1) + ' KB';
            tr.innerHTML = `
                <td class="px-4 py-3 text-sm font-mono text-slate-700 dark:text-slate-200">${escapeHtml(f.filename)}</td>
                <td class="px-4 py-3 text-sm">${typeLabel}</td>
                <td class="px-4 py-3 text-sm text-slate-500 dark:text-slate-400">${sizeStr}</td>
                <td class="px-4 py-3 text-sm text-slate-500 dark:text-slate-400">${escapeHtml(f.updated_at)}</td>`;
            tbody.appendChild(tr);
        });

        // Pagination
        const totalPages = Math.ceil(total / memoryPageSize);
        const pagEl = document.getElementById('memory-pagination');
        if (totalPages <= 1) { pagEl.innerHTML = ''; return; }
        let pagHtml = `<span>${page} / ${totalPages}</span><div class="flex gap-2">`;
        if (page > 1) pagHtml += `<button onclick="loadMemoryView(${page - 1})" class="px-3 py-1 rounded-lg border border-slate-200 dark:border-white/10 hover:bg-slate-100 dark:hover:bg-white/10 text-xs">Prev</button>`;
        if (page < totalPages) pagHtml += `<button onclick="loadMemoryView(${page + 1})" class="px-3 py-1 rounded-lg border border-slate-200 dark:border-white/10 hover:bg-slate-100 dark:hover:bg-white/10 text-xs">Next</button>`;
        pagHtml += '</div>';
        pagEl.innerHTML = pagHtml;
    }).catch(() => {});
}

function openMemoryFile(filename, category) {
    category = category || 'memory';
    fetch(appendAgentQuery(`/api/memory/content?filename=${encodeURIComponent(filename)}&category=${category}`)).then(r => r.json()).then(data => {
        if (data.status !== 'success') return;
        document.getElementById('memory-panel-list').classList.add('hidden');
        const panel = document.getElementById('memory-panel-viewer');
        document.getElementById('memory-viewer-title').textContent = filename;
        document.getElementById('memory-viewer-content').innerHTML = renderMarkdown(data.content || '');
        panel.classList.remove('hidden');
        applyHighlighting(panel);
    }).catch(() => {});
}

function closeMemoryViewer() {
    document.getElementById('memory-panel-viewer').classList.add('hidden');
    document.getElementById('memory-panel-list').classList.remove('hidden');
}

// =====================================================================
// Custom Confirm Dialog
// =====================================================================
function showConfirmDialog({ title, message, okText, cancelText, onConfirm }) {
    const overlay = document.getElementById('confirm-dialog-overlay');
    document.getElementById('confirm-dialog-title').textContent = title || '';
    document.getElementById('confirm-dialog-message').textContent = message || '';
    document.getElementById('confirm-dialog-ok').textContent = okText || 'OK';
    document.getElementById('confirm-dialog-cancel').textContent = cancelText || t('channels_cancel');

    function cleanup() {
        overlay.classList.add('hidden');
        okBtn.removeEventListener('click', onOk);
        cancelBtn.removeEventListener('click', onCancel);
        overlay.removeEventListener('click', onOverlayClick);
    }
    function onOk() { cleanup(); if (onConfirm) onConfirm(); }
    function onCancel() { cleanup(); }
    function onOverlayClick(e) { if (e.target === overlay) cleanup(); }

    const okBtn = document.getElementById('confirm-dialog-ok');
    const cancelBtn = document.getElementById('confirm-dialog-cancel');
    okBtn.addEventListener('click', onOk);
    cancelBtn.addEventListener('click', onCancel);
    overlay.addEventListener('click', onOverlayClick);
    overlay.classList.remove('hidden');
}

// =====================================================================
// Channels View
// =====================================================================
let channelsData = [];

function loadChannelsView() {
    const container = document.getElementById('channels-content');
    container.innerHTML = `<div class="flex items-center gap-2 py-8 justify-center text-slate-400 dark:text-slate-500 text-sm">
        <i class="fas fa-spinner fa-spin text-xs"></i><span>Loading...</span></div>`;

    fetch('/api/channels').then(r => r.json()).then(data => {
        if (data.status !== 'success') return;
        channelsData = data.channels || [];
        renderActiveChannels();
    }).catch(() => {
        container.innerHTML = '<p class="text-sm text-red-400 py-8 text-center">Failed to load channels</p>';
    });
}

function renderActiveChannels() {
    stopWeixinQrPoll();
    stopWeixinStatusPoll();
    const container = document.getElementById('channels-content');
    container.innerHTML = '';
    closeAddChannelPanel();

    const activeChannels = channelsData.filter(ch => ch.active);

    if (activeChannels.length === 0) {
        container.innerHTML = `
            <div class="flex flex-col items-center justify-center py-20">
                <div class="w-16 h-16 rounded-2xl bg-blue-50 dark:bg-blue-900/20 flex items-center justify-center mb-4">
                    <i class="fas fa-tower-broadcast text-blue-400 text-xl"></i>
                </div>
                <p class="text-slate-500 dark:text-slate-400 font-medium">${t('channels_empty')}</p>
                <p class="text-sm text-slate-400 dark:text-slate-500 mt-1">${t('channels_empty_desc')}</p>
            </div>`;
        return;
    }

    activeChannels.forEach(ch => {
        const label = (typeof ch.label === 'object') ? (ch.label[currentLang] || ch.label.en) : ch.label;
        const card = document.createElement('div');
        card.className = 'bg-white dark:bg-[#1A1A1A] rounded-xl border border-slate-200 dark:border-white/10 p-6';
        card.id = `channel-card-${ch.name}`;

        const fieldsHtml = buildChannelFieldsHtml(ch.name, ch.fields || []);
        const hasFields = (ch.fields || []).length > 0;

        const weixinWaiting = ch.name === 'weixin' && ch.login_status && ch.login_status !== 'logged_in';
        const wecomNeedsCreds = ch.name === 'wecom_bot' && !_wecomBotHasCreds(ch);
        let statusDot, statusText;
        if (weixinWaiting) {
            statusDot = 'bg-amber-400 animate-pulse';
            statusText = ch.login_status === 'scanned'
                ? `<span class="text-xs text-primary-500">${t('weixin_scan_scanned')}</span>`
                : `<span class="text-xs text-amber-500">${t('weixin_scan_waiting')}</span>`;
        } else if (wecomNeedsCreds) {
            statusDot = 'bg-amber-400 animate-pulse';
            statusText = `<span class="text-xs text-amber-500">${t('channels_connecting')}</span>`;
        } else {
            statusDot = 'bg-primary-400';
            statusText = `<span class="text-xs text-primary-500">${t('channels_connected')}</span>`;
        }

        card.innerHTML = `
            <div class="flex items-center gap-4${hasFields || weixinWaiting || wecomNeedsCreds ? ' mb-5' : ''}">
                <div class="w-10 h-10 rounded-xl bg-${ch.color}-50 dark:bg-${ch.color}-900/20 flex items-center justify-center flex-shrink-0">
                    <i class="fas ${ch.icon} text-${ch.color}-500 text-base"></i>
                </div>
                <div class="flex-1 min-w-0">
                    <div class="flex items-center gap-2">
                        <span class="font-semibold text-slate-800 dark:text-slate-100">${escapeHtml(label)}</span>
                        <span class="w-2 h-2 rounded-full ${statusDot}"></span>
                        ${statusText}
                    </div>
                    <p class="text-xs text-slate-500 dark:text-slate-400 mt-0.5 font-mono">${escapeHtml(ch.name)}</p>
                </div>
                <button onclick="disconnectChannel('${ch.name}')"
                    class="px-3 py-1.5 rounded-lg text-xs font-medium
                           bg-red-50 dark:bg-red-900/20 text-red-500 dark:text-red-400
                           hover:bg-red-100 dark:hover:bg-red-900/40
                           cursor-pointer transition-colors flex-shrink-0">
                    ${t('channels_disconnect')}
                </button>
            </div>
            ${weixinWaiting ? `<div id="weixin-active-qr" class="flex flex-col items-center py-2">
                <button onclick="showWeixinActiveQr()"
                    class="px-4 py-2 rounded-lg bg-primary-500 hover:bg-primary-600 text-white text-sm font-medium
                           cursor-pointer transition-colors duration-150">
                    ${t('weixin_scan_title')}
                </button>
            </div>` : ''}
            ${wecomNeedsCreds ? `<div id="wecom-active-auth" class="flex flex-col items-center py-2">
                <p class="text-sm text-slate-500 dark:text-slate-400 mb-3">${t('wecom_scan_desc')}</p>
                <button onclick="startWecomBotAuthInCard()"
                    class="px-5 py-2 rounded-lg bg-emerald-500 hover:bg-emerald-600 text-white text-sm font-medium
                           cursor-pointer transition-colors duration-150">
                    <i class="fas fa-qrcode mr-2"></i>${t('wecom_scan_btn')}
                </button>
                <div id="wecom-card-scan-status" class="mt-3"></div>
            </div>` : ''}
            ${hasFields ? `<div class="space-y-4">
                ${fieldsHtml}
                <div class="flex items-center justify-end gap-3 pt-1">
                    <span id="ch-status-${ch.name}" class="text-xs text-primary-500 opacity-0 transition-opacity duration-300"></span>
                    <button onclick="saveChannelConfig('${ch.name}')"
                        class="px-4 py-2 rounded-lg bg-primary-500 hover:bg-primary-600 text-white text-sm font-medium
                               cursor-pointer transition-colors duration-150 disabled:opacity-50 disabled:cursor-not-allowed"
                        id="ch-save-${ch.name}">${t('channels_save')}</button>
                </div>
            </div>` : ''}`;

        container.appendChild(card);
        bindSecretFieldEvents(card);

        if (weixinWaiting) {
            startWeixinActiveStatusPoll();
        }
    });
}

function buildChannelFieldsHtml(chName, fields) {
    let html = '';
    fields.forEach(f => {
        const inputId = `ch-${chName}-${f.key}`;
        let inputHtml = '';
        if (f.type === 'bool') {
            const checked = f.value ? 'checked' : '';
            inputHtml = `<label class="relative inline-flex items-center cursor-pointer">
                <input id="${inputId}" type="checkbox" ${checked} class="sr-only peer" data-field="${f.key}" data-ch="${chName}">
                <div class="w-9 h-5 bg-slate-200 dark:bg-slate-700 peer-checked:bg-primary-400 rounded-full
                            after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white
                            after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:after:translate-x-full"></div>
            </label>`;
        } else if (f.type === 'secret') {
            inputHtml = `<input id="${inputId}" type="text" value="${escapeHtml(String(f.value || ''))}"
                data-field="${f.key}" data-ch="${chName}" data-masked="${f.value ? '1' : ''}"
                class="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-600
                       bg-slate-50 dark:bg-white/5 text-sm text-slate-800 dark:text-slate-100
                       focus:outline-none focus:border-primary-500 font-mono transition-colors
                       ${f.value ? 'cfg-key-masked' : ''}"
                placeholder="${escapeHtml(f.label)}">`;
        } else {
            const inputType = f.type === 'number' ? 'number' : 'text';
            inputHtml = `<input id="${inputId}" type="${inputType}" value="${escapeHtml(String(f.value ?? f.default ?? ''))}"
                data-field="${f.key}" data-ch="${chName}"
                class="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-600
                       bg-slate-50 dark:bg-white/5 text-sm text-slate-800 dark:text-slate-100
                       focus:outline-none focus:border-primary-500 font-mono transition-colors"
                placeholder="${escapeHtml(f.label)}">`;
        }
        html += `<div>
            <label class="block text-sm font-medium text-slate-600 dark:text-slate-400 mb-1.5">${escapeHtml(f.label)}</label>
            ${inputHtml}
        </div>`;
    });
    return html;
}

function bindSecretFieldEvents(container) {
    container.querySelectorAll('input[data-masked="1"]').forEach(inp => {
        inp.addEventListener('focus', function() {
            if (this.dataset.masked === '1') {
                this.value = '';
                this.dataset.masked = '';
                this.classList.remove('cfg-key-masked');
            }
        });
    });
}

function showChannelStatus(chName, msgKey, isError) {
    const el = document.getElementById(`ch-status-${chName}`);
    if (!el) return;
    el.textContent = t(msgKey);
    el.classList.toggle('text-red-500', !!isError);
    el.classList.toggle('text-primary-500', !isError);
    el.classList.remove('opacity-0');
    setTimeout(() => el.classList.add('opacity-0'), 2500);
}

function saveChannelConfig(chName) {
    const card = document.getElementById(`channel-card-${chName}`);
    if (!card) return;

    const updates = {};
    card.querySelectorAll('input[data-ch="' + chName + '"]').forEach(inp => {
        const key = inp.dataset.field;
        if (inp.type === 'checkbox') {
            updates[key] = inp.checked;
        } else {
            if (inp.dataset.masked === '1') return;
            updates[key] = inp.value;
        }
    });

    const btn = document.getElementById(`ch-save-${chName}`);
    if (btn) btn.disabled = true;

    fetch('/api/channels', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'save', channel: chName, config: updates })
    })
    .then(r => r.json())
    .then(data => {
        if (data.status === 'success') {
            showChannelStatus(chName, data.restarted ? 'channels_restarted' : 'channels_saved', false);
        } else {
            showChannelStatus(chName, 'channels_save_error', true);
        }
    })
    .catch(() => showChannelStatus(chName, 'channels_save_error', true))
    .finally(() => { if (btn) btn.disabled = false; });
}

function disconnectChannel(chName) {
    const ch = channelsData.find(c => c.name === chName);
    const label = ch ? ((typeof ch.label === 'object') ? (ch.label[currentLang] || ch.label.en) : ch.label) : chName;

    showConfirmDialog({
        title: t('channels_disconnect'),
        message: t('channels_disconnect_confirm'),
        okText: t('channels_disconnect'),
        cancelText: t('channels_cancel'),
        onConfirm: () => {
            fetch('/api/channels', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ action: 'disconnect', channel: chName })
            })
            .then(r => r.json())
            .then(data => {
                if (data.status === 'success') {
                    if (ch) ch.active = false;
                    renderActiveChannels();
                }
            })
            .catch(() => {});
        }
    });
}

// --- Add channel panel ---
function openAddChannelPanel() {
    const panel = document.getElementById('channels-add-panel');
    const activeNames = new Set(channelsData.filter(c => c.active).map(c => c.name));
    const available = channelsData.filter(c => !activeNames.has(c.name));

    const content = document.getElementById('channels-content');
    if (activeNames.size === 0 && content) content.classList.add('hidden');

    if (available.length === 0) {
        panel.innerHTML = `<div class="bg-white dark:bg-[#1A1A1A] rounded-xl border border-slate-200 dark:border-white/10 p-6 text-center">
            <p class="text-sm text-slate-500 dark:text-slate-400">${currentLang === 'zh' ? '所有通道均已接入' : 'All channels are already connected'}</p>
            <button onclick="closeAddChannelPanel()" class="mt-3 text-xs text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 cursor-pointer">${t('channels_cancel')}</button>
        </div>`;
        panel.classList.remove('hidden');
        return;
    }

    const ddOptions = [
        { value: '', label: t('channels_select_placeholder') },
        ...available.map(ch => {
            const label = (typeof ch.label === 'object') ? (ch.label[currentLang] || ch.label.en) : ch.label;
            return { value: ch.name, label: `${label} (${ch.name})` };
        })
    ];

    panel.innerHTML = `
        <div class="bg-white dark:bg-[#1A1A1A] rounded-xl border border-primary-200 dark:border-primary-800 p-6">
            <div class="flex items-center gap-3 mb-5">
                <div class="w-9 h-9 rounded-lg bg-primary-50 dark:bg-primary-900/30 flex items-center justify-center">
                    <i class="fas fa-plus text-primary-500 text-sm"></i>
                </div>
                <h3 class="font-semibold text-slate-800 dark:text-slate-100">${t('channels_add')}</h3>
            </div>
            <div class="mb-4">
                <div id="add-channel-select" class="cfg-dropdown" tabindex="0">
                    <div class="cfg-dropdown-selected">
                        <span class="cfg-dropdown-text">--</span>
                        <i class="fas fa-chevron-down cfg-dropdown-arrow"></i>
                    </div>
                    <div class="cfg-dropdown-menu"></div>
                </div>
            </div>
            <div id="add-channel-fields" class="space-y-4"></div>
            <div id="add-channel-actions" class="hidden flex items-center justify-end gap-3 pt-4">
                <button onclick="closeAddChannelPanel()"
                    class="px-4 py-2 rounded-lg border border-slate-200 dark:border-white/10
                           text-slate-600 dark:text-slate-300 text-sm font-medium
                           hover:bg-slate-50 dark:hover:bg-white/5
                           cursor-pointer transition-colors duration-150">${t('channels_cancel')}</button>
                <button id="add-channel-submit" onclick="submitAddChannel()"
                    class="px-4 py-2 rounded-lg bg-primary-500 hover:bg-primary-600 text-white text-sm font-medium
                           cursor-pointer transition-colors duration-150 disabled:opacity-50 disabled:cursor-not-allowed">${t('channels_connect_btn')}</button>
            </div>
        </div>`;
    panel.classList.remove('hidden');
    panel.scrollIntoView({ behavior: 'smooth', block: 'nearest' });

    const ddEl = document.getElementById('add-channel-select');
    initDropdown(ddEl, ddOptions, '', onAddChannelSelect);
}

function closeAddChannelPanel() {
    stopWeixinQrPoll();
    const panel = document.getElementById('channels-add-panel');
    if (panel) {
        panel.classList.add('hidden');
        panel.innerHTML = '';
    }
    const content = document.getElementById('channels-content');
    if (content) content.classList.remove('hidden');
}

function onAddChannelSelect(chName) {
    stopWeixinQrPoll();
    const fieldsContainer = document.getElementById('add-channel-fields');
    const actions = document.getElementById('add-channel-actions');

    if (!chName) {
        fieldsContainer.innerHTML = '';
        actions.classList.add('hidden');
        return;
    }

    if (chName === 'weixin') {
        actions.classList.add('hidden');
        fieldsContainer.innerHTML = `
            <div id="weixin-qr-panel" class="flex flex-col items-center py-4">
                <p class="text-sm text-slate-500 dark:text-slate-400 mb-4">${t('weixin_scan_loading')}</p>
            </div>`;
        startWeixinQrLogin();
        return;
    }

    if (chName === 'wecom_bot') {
        actions.classList.add('hidden');
        const ch = channelsData.find(c => c.name === chName);
        fieldsContainer.innerHTML = buildWecomBotPanel(ch);
        return;
    }

    const ch = channelsData.find(c => c.name === chName);
    if (!ch) return;

    fieldsContainer.innerHTML = buildChannelFieldsHtml(chName, ch.fields || []);
    bindSecretFieldEvents(fieldsContainer);
    actions.classList.remove('hidden');
}

function submitAddChannel() {
    const ddEl = document.getElementById('add-channel-select');
    const chName = getDropdownValue(ddEl);
    if (!chName) return;

    const fieldsContainer = document.getElementById('add-channel-fields');
    const updates = {};
    fieldsContainer.querySelectorAll('input[data-ch="' + chName + '"]').forEach(inp => {
        const key = inp.dataset.field;
        if (inp.type === 'checkbox') {
            updates[key] = inp.checked;
        } else {
            if (inp.dataset.masked === '1') return;
            updates[key] = inp.value;
        }
    });

    const btn = document.getElementById('add-channel-submit');
    if (btn) { btn.disabled = true; btn.textContent = t('channels_connecting'); }

    fetch('/api/channels', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'connect', channel: chName, config: updates })
    })
    .then(r => r.json())
    .then(data => {
        if (data.status === 'success') {
            const ch = channelsData.find(c => c.name === chName);
            if (ch) {
                ch.active = true;
                (ch.fields || []).forEach(f => {
                    if (updates[f.key] !== undefined) {
                        f.value = f.type === 'secret' ? ChannelsHandler_maskSecret(updates[f.key]) : updates[f.key];
                    }
                });
            }
            renderActiveChannels();
        } else {
            if (btn) { btn.disabled = false; btn.textContent = t('channels_connect_btn'); }
        }
    })
    .catch(() => {
        if (btn) { btn.disabled = false; btn.textContent = t('channels_connect_btn'); }
    });
}

// =====================================================================
// WeChat QR Login
// =====================================================================
let _weixinQrPollTimer = null;
let _weixinStatusPollTimer = null;

function stopWeixinStatusPoll() {
    if (_weixinStatusPollTimer) {
        clearTimeout(_weixinStatusPollTimer);
        _weixinStatusPollTimer = null;
    }
}

function startWeixinActiveStatusPoll() {
    stopWeixinStatusPoll();
    _weixinStatusPollTimer = setTimeout(() => {
        fetch('/api/channels').then(r => r.json()).then(data => {
            if (data.status !== 'success') return;
            const wx = (data.channels || []).find(c => c.name === 'weixin');
            if (!wx || !wx.active) return;
            if (wx.login_status === 'logged_in') {
                channelsData = data.channels;
                renderActiveChannels();
            } else {
                const ch = channelsData.find(c => c.name === 'weixin');
                if (ch) ch.login_status = wx.login_status;
                startWeixinActiveStatusPoll();
            }
        }).catch(() => { startWeixinActiveStatusPoll(); });
    }, 3000);
}

function showWeixinActiveQr() {
    const container = document.getElementById('weixin-active-qr');
    if (!container) return;
    container.innerHTML = `
        <div id="weixin-qr-panel" class="flex flex-col items-center py-2">
            <p class="text-sm text-slate-500 dark:text-slate-400 mb-4">${t('weixin_scan_loading')}</p>
        </div>`;
    stopWeixinStatusPoll();
    startWeixinQrLogin();
}

function stopWeixinQrPoll() {
    if (_weixinQrPollTimer) {
        clearTimeout(_weixinQrPollTimer);
        _weixinQrPollTimer = null;
    }
}

function startWeixinQrLogin() {
    stopWeixinQrPoll();
    fetch('/api/weixin/qrlogin')
        .then(r => r.json())
        .then(data => {
            const panel = document.getElementById('weixin-qr-panel');
            if (!panel) return;
            if (data.status !== 'success') {
                panel.innerHTML = `<p class="text-sm text-red-500">${t('weixin_scan_fail')}: ${data.message || ''}</p>`;
                return;
            }
            renderWeixinQr(data.qr_image || data.qrcode_url, 'waiting');
            if (data.source === 'channel') {
                startWeixinActiveStatusPoll();
            } else {
                pollWeixinQrStatus();
            }
        })
        .catch(() => {
            const panel = document.getElementById('weixin-qr-panel');
            if (panel) panel.innerHTML = `<p class="text-sm text-red-500">${t('weixin_scan_fail')}</p>`;
        });
}

function renderWeixinQr(qrcodeUrl, status) {
    const panel = document.getElementById('weixin-qr-panel');
    if (!panel) return;

    let statusText = t('weixin_scan_waiting');
    let statusColor = 'text-slate-500 dark:text-slate-400';
    if (status === 'scanned') {
        statusText = t('weixin_scan_scanned');
        statusColor = 'text-primary-500';
    } else if (status === 'expired') {
        statusText = t('weixin_scan_expired');
        statusColor = 'text-amber-500';
    } else if (status === 'confirmed') {
        statusText = t('weixin_scan_success');
        statusColor = 'text-primary-500';
    }

    panel.innerHTML = `
        <div class="flex flex-col items-center">
            <p class="text-sm font-medium text-slate-700 dark:text-slate-200 mb-1">${t('weixin_scan_title')}</p>
            <p class="text-xs text-slate-400 dark:text-slate-500 mb-4">${t('weixin_scan_desc')}</p>
            <div class="bg-white p-3 rounded-xl shadow-sm border border-slate-100 dark:border-slate-700 mb-3">
                <img src="${escapeHtml(qrcodeUrl)}" alt="QR Code" class="w-52 h-52" style="image-rendering: pixelated;"/>
            </div>
            <p class="text-xs ${statusColor} mb-1">${statusText}</p>
            <p class="text-xs text-slate-400 dark:text-slate-500">${t('weixin_qr_tip')}</p>
        </div>`;
}

function pollWeixinQrStatus() {
    _weixinQrPollTimer = setTimeout(() => {
        fetch('/api/weixin/qrlogin', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action: 'poll' })
        })
        .then(r => r.json())
        .then(data => {
            const panel = document.getElementById('weixin-qr-panel');
            if (!panel) { stopWeixinQrPoll(); return; }

            if (data.status !== 'success') {
                pollWeixinQrStatus();
                return;
            }

            const qrStatus = data.qr_status;
            if (qrStatus === 'confirmed') {
                renderWeixinQr('', 'confirmed');
                panel.innerHTML = `
                    <div class="flex flex-col items-center py-4">
                        <div class="w-12 h-12 rounded-full bg-primary-50 dark:bg-primary-900/30 flex items-center justify-center mb-3">
                            <i class="fas fa-check text-primary-500 text-lg"></i>
                        </div>
                        <p class="text-sm font-medium text-primary-600 dark:text-primary-400">${t('weixin_scan_success')}</p>
                    </div>`;
                connectWeixinAfterQr();
            } else if (qrStatus === 'expired' && (data.qr_image || data.qrcode_url)) {
                renderWeixinQr(data.qr_image || data.qrcode_url, 'waiting');
                pollWeixinQrStatus();
            } else if (qrStatus === 'scaned') {
                const img = panel.querySelector('img');
                const currentSrc = img ? img.src : '';
                renderWeixinQr(currentSrc, 'scanned');
                pollWeixinQrStatus();
            } else {
                pollWeixinQrStatus();
            }
        })
        .catch(() => {
            pollWeixinQrStatus();
        });
    }, 2000);
}

function connectWeixinAfterQr() {
    fetch('/api/channels', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'connect', channel: 'weixin', config: {} })
    })
    .then(r => r.json())
    .then(data => {
        if (data.status === 'success') {
            const ch = channelsData.find(c => c.name === 'weixin');
            if (ch) ch.active = true;
            setTimeout(() => renderActiveChannels(), 1500);
        }
    })
    .catch(() => {});
}

// =====================================================================
// WeCom Bot QR Auth
// =====================================================================
const WECOM_BOT_SDK_URL = 'https://wwcdn.weixin.qq.com/node/wework/js/wecom-aibot-sdk@0.1.0.min.js';
const WECOM_BOT_SOURCE = 'cowagent';
let _wecomSdkLoaded = false;

function ensureWecomSdkLoaded() {
    return new Promise((resolve, reject) => {
        if (_wecomSdkLoaded && window.WecomAIBotSDK) { resolve(); return; }
        if (document.querySelector(`script[src="${WECOM_BOT_SDK_URL}"]`)) {
            _wecomSdkLoaded = true; resolve(); return;
        }
        const s = document.createElement('script');
        s.src = WECOM_BOT_SDK_URL;
        s.onload = () => { _wecomSdkLoaded = true; resolve(); };
        s.onerror = () => reject(new Error('Failed to load WecomAIBotSDK'));
        document.head.appendChild(s);
    });
}

function _wecomBotHasCreds(ch) {
    if (!ch || !ch.fields) return false;
    const idField = ch.fields.find(f => f.key === 'wecom_bot_id');
    const secretField = ch.fields.find(f => f.key === 'wecom_bot_secret');
    return !!(idField && idField.value && secretField && secretField.value);
}

function buildWecomBotPanel(ch) {
    const scanLabel = t('wecom_mode_scan');
    const manualLabel = t('wecom_mode_manual');
    const hasCreds = _wecomBotHasCreds(ch);
    const defaultMode = hasCreds ? 'manual' : 'scan';
    return `
        <div id="wecom-bot-panel" data-default-mode="${defaultMode}">
            <div class="flex items-center justify-center gap-1 mb-5 bg-slate-100 dark:bg-white/5 rounded-lg p-1">
                <button id="wecom-tab-scan" onclick="switchWecomBotMode('scan')"
                    class="flex-1 px-3 py-1.5 rounded-md text-xs font-medium transition-colors
                           bg-white dark:bg-slate-700 text-slate-800 dark:text-slate-100 shadow-sm">
                    ${scanLabel}
                </button>
                <button id="wecom-tab-manual" onclick="switchWecomBotMode('manual')"
                    class="flex-1 px-3 py-1.5 rounded-md text-xs font-medium transition-colors
                           text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-200">
                    ${manualLabel}
                </button>
            </div>
            <div id="wecom-mode-content"></div>
        </div>`;
}

function switchWecomBotMode(mode) {
    const scanTab = document.getElementById('wecom-tab-scan');
    const manualTab = document.getElementById('wecom-tab-manual');
    const content = document.getElementById('wecom-mode-content');
    const actions = document.getElementById('add-channel-actions');
    if (!scanTab || !manualTab || !content) return;

    const activeClasses = 'bg-white dark:bg-slate-700 text-slate-800 dark:text-slate-100 shadow-sm';
    const inactiveClasses = 'text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-200';

    if (mode === 'scan') {
        scanTab.className = scanTab.className.replace(/text-slate-500[^\s]*/g, '').replace(/hover:\S+/g, '');
        scanTab.className = `flex-1 px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${activeClasses}`;
        manualTab.className = `flex-1 px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${inactiveClasses}`;
        actions.classList.add('hidden');
        content.innerHTML = `
            <div class="flex flex-col items-center py-4">
                <p class="text-sm text-slate-600 dark:text-slate-300 mb-2">${t('wecom_scan_desc')}</p>
                <button onclick="startWecomBotAuth()"
                    class="mt-3 px-6 py-2.5 rounded-lg bg-emerald-500 hover:bg-emerald-600 text-white text-sm font-medium
                           cursor-pointer transition-colors duration-150">
                    <i class="fas fa-qrcode mr-2"></i>${t('wecom_scan_btn')}
                </button>
                <div id="wecom-scan-status" class="mt-3"></div>
            </div>`;
    } else {
        manualTab.className = `flex-1 px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${activeClasses}`;
        scanTab.className = `flex-1 px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${inactiveClasses}`;
        const ch = channelsData.find(c => c.name === 'wecom_bot');
        content.innerHTML = `<div class="space-y-4">${buildChannelFieldsHtml('wecom_bot', ch ? ch.fields || [] : [])}</div>`;
        bindSecretFieldEvents(content);
        actions.classList.remove('hidden');
    }
}

function startWecomBotAuth() {
    const statusEl = document.getElementById('wecom-scan-status');
    ensureWecomSdkLoaded().then(() => {
        WecomAIBotSDK.openBotInfoAuthWindow({
            source: WECOM_BOT_SOURCE,
            onCreated: function(bot) {
                if (statusEl) {
                    statusEl.innerHTML = `
                        <div class="flex flex-col items-center py-2">
                            <div class="w-10 h-10 rounded-full bg-emerald-50 dark:bg-emerald-900/30 flex items-center justify-center mb-2">
                                <i class="fas fa-check text-emerald-500 text-lg"></i>
                            </div>
                            <p class="text-sm font-medium text-emerald-600 dark:text-emerald-400">${t('wecom_scan_success')}</p>
                        </div>`;
                }
                connectWecomBotAfterAuth(bot.botid, bot.secret);
            },
            onError: function(err) {
                if (statusEl) {
                    statusEl.innerHTML = `<p class="text-sm text-red-500">${t('wecom_scan_fail')}: ${err.message || err.code || ''}</p>`;
                }
            }
        });
    }).catch(err => {
        if (statusEl) {
            statusEl.innerHTML = `<p class="text-sm text-red-500">SDK load failed: ${err.message}</p>`;
        }
    });
}

function connectWecomBotAfterAuth(botId, secret) {
    fetch('/api/channels', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            action: 'connect',
            channel: 'wecom_bot',
            config: { wecom_bot_id: botId, wecom_bot_secret: secret }
        })
    })
    .then(r => r.json())
    .then(data => {
        if (data.status === 'success') {
            const ch = channelsData.find(c => c.name === 'wecom_bot');
            if (ch) {
                ch.active = true;
                (ch.fields || []).forEach(f => {
                    if (f.key === 'wecom_bot_id') f.value = botId;
                    if (f.key === 'wecom_bot_secret') f.value = ChannelsHandler_maskSecret(secret);
                });
            }
            setTimeout(() => renderActiveChannels(), 1500);
        }
    })
    .catch(() => {});
}

function startWecomBotAuthInCard() {
    const statusEl = document.getElementById('wecom-card-scan-status');
    ensureWecomSdkLoaded().then(() => {
        WecomAIBotSDK.openBotInfoAuthWindow({
            source: WECOM_BOT_SOURCE,
            onCreated: function(bot) {
                if (statusEl) {
                    statusEl.innerHTML = `
                        <div class="flex flex-col items-center py-2">
                            <div class="w-10 h-10 rounded-full bg-emerald-50 dark:bg-emerald-900/30 flex items-center justify-center mb-2">
                                <i class="fas fa-check text-emerald-500 text-lg"></i>
                            </div>
                            <p class="text-sm font-medium text-emerald-600 dark:text-emerald-400">${t('wecom_scan_success')}</p>
                        </div>`;
                }
                connectWecomBotAfterAuth(bot.botid, bot.secret);
            },
            onError: function(err) {
                if (statusEl) {
                    statusEl.innerHTML = `<p class="text-sm text-red-500">${t('wecom_scan_fail')}: ${err.message || err.code || ''}</p>`;
                }
            }
        });
    }).catch(err => {
        if (statusEl) {
            statusEl.innerHTML = `<p class="text-sm text-red-500">SDK load failed: ${err.message}</p>`;
        }
    });
}

// Initialize wecom bot panel with correct default mode when inserted into DOM
document.addEventListener('DOMContentLoaded', function() {
    const observer = new MutationObserver(function() {
        const panel = document.getElementById('wecom-bot-panel');
        if (panel && !panel.dataset.initialized) {
            panel.dataset.initialized = '1';
            switchWecomBotMode(panel.dataset.defaultMode || 'scan');
        }
    });
    observer.observe(document.body, { childList: true, subtree: true });
});

// =====================================================================
// Scheduler View
// =====================================================================
let tasksLoaded = false;
function loadTasksView() {
    if (tasksLoaded) return;
    fetch(appendAgentQuery('/api/scheduler')).then(r => r.json()).then(data => {
        if (data.status !== 'success') return;
        const emptyEl = document.getElementById('tasks-empty');
        const listEl = document.getElementById('tasks-list');
        const allTasks = data.tasks || [];
        // Only show active (enabled) tasks
        const tasks = allTasks.filter(t => t.enabled !== false);
        if (tasks.length === 0) {
            emptyEl.querySelector('p').textContent = currentLang === 'zh' ? '暂无定时任务' : 'No scheduled tasks';
            return;
        }
        emptyEl.classList.add('hidden');
        listEl.classList.remove('hidden');
        listEl.innerHTML = '';

        tasks.forEach(task => {
            const card = document.createElement('div');
            card.className = 'bg-white dark:bg-[#1A1A1A] rounded-xl border border-slate-200 dark:border-white/10 p-4';
            const typeLabel = task.type === 'cron'
                ? `<span class="text-xs font-mono text-slate-400">${escapeHtml(task.cron || '')}</span>`
                : `<span class="text-xs text-slate-400">${escapeHtml(task.type || 'once')}</span>`;
            let nextRun = '--';
            if (task.next_run_at) {
                // next_run_at is an ISO string, not a Unix timestamp
                const d = new Date(task.next_run_at);
                if (!isNaN(d.getTime())) nextRun = d.toLocaleString();
            }
            card.innerHTML = `
                <div class="flex items-center gap-2 mb-2">
                    <span class="w-2 h-2 rounded-full bg-primary-400"></span>
                    <span class="font-medium text-sm text-slate-700 dark:text-slate-200">${escapeHtml(task.name || task.id || '--')}</span>
                    <div class="flex-1"></div>
                    ${typeLabel}
                </div>
                <p class="text-xs text-slate-500 dark:text-slate-400 mb-2 line-clamp-2">${escapeHtml(task.prompt || task.description || '')}</p>
                <div class="flex items-center gap-4 text-xs text-slate-400 dark:text-slate-500">
                    <span><i class="fas fa-clock mr-1"></i>${currentLang === 'zh' ? '下次执行' : 'Next run'}: ${nextRun}</span>
                </div>`;
            listEl.appendChild(card);
        });
        tasksLoaded = true;
    }).catch(() => {});
}

// =====================================================================
// Logs View
// =====================================================================
let logEventSource = null;

function startLogStream() {
    if (logEventSource) return;
    const output = document.getElementById('log-output');
    output.innerHTML = '';

    logEventSource = new EventSource('/api/logs');
    logEventSource.onmessage = function(e) {
        let item;
        try { item = JSON.parse(e.data); } catch (_) { return; }

        if (item.type === 'init') {
            output.textContent = item.content || '';
            output.scrollTop = output.scrollHeight;
        } else if (item.type === 'line') {
            output.textContent += item.content;
            output.scrollTop = output.scrollHeight;
        } else if (item.type === 'error') {
            output.textContent = item.message || 'Error loading logs';
        }
    };
    logEventSource.onerror = function() {
        logEventSource.close();
        logEventSource = null;
    };
}

function stopLogStream() {
    if (logEventSource) {
        logEventSource.close();
        logEventSource = null;
    }
}

// =====================================================================
// View Navigation Hook
// =====================================================================
const _origNavigateTo = navigateTo;
navigateTo = function(viewId) {
    // Stop log stream when leaving logs view
    if (currentView === 'logs' && viewId !== 'logs') stopLogStream();

    _origNavigateTo(viewId);

    // Lazy-load view data
    if (viewId === 'config') loadConfigView();
    else if (viewId === 'skills') loadSkillsView();
    else if (viewId === 'agents') loadAgentsView();
    else if (viewId === 'bindings') loadBindingsView();
    else if (viewId === 'tenants') loadTenantsView();
    else if (viewId === 'tenant_users') loadTenantUsersView();
    else if (viewId === 'mcp') loadMcpView();
    else if (viewId === 'memory') {
        document.getElementById('memory-panel-viewer').classList.add('hidden');
        document.getElementById('memory-panel-list').classList.remove('hidden');
        switchMemoryTab('files');
    }
    else if (viewId === 'knowledge') loadKnowledgeView();
    else if (viewId === 'channels') loadChannelsView();
    else if (viewId === 'tasks') loadTasksView();
    else if (viewId === 'logs') startLogStream();
};

// =====================================================================
// Knowledge View
// =====================================================================
let _knowledgeTreeData = [];
let _knowledgeCurrentFile = null;
let _knowledgeGraphLoaded = false;

function loadKnowledgeView() {
    // Reset to docs tab
    switchKnowledgeTab('docs');
    _knowledgeGraphLoaded = false;
    _knowledgeCurrentFile = null;

    fetch(appendAgentQuery('/api/knowledge/list')).then(r => r.json()).then(data => {
        if (data.status !== 'success') return;

        const emptyEl = document.getElementById('knowledge-empty');
        const docsPanel = document.getElementById('knowledge-panel-docs');
        const statsEl = document.getElementById('knowledge-stats');

        const tree = data.tree || [];
        _knowledgeTreeData = tree;
        const stats = data.stats || {};
        const totalPages = stats.pages || 0;
        const sizeStr = stats.size < 1024 ? stats.size + ' B' : (stats.size / 1024).toFixed(1) + ' KB';

        statsEl.textContent = totalPages + ' pages · ' + sizeStr;

        if (totalPages === 0) {
            emptyEl.querySelector('p').textContent = t('knowledge_empty_hint');
            const guideEl = document.getElementById('knowledge-empty-guide');
            if (guideEl) guideEl.classList.remove('hidden');
            emptyEl.classList.remove('hidden');
            docsPanel.classList.add('hidden');
            return;
        }
        emptyEl.classList.add('hidden');
        docsPanel.classList.remove('hidden');

        renderKnowledgeTree(tree);

        // Auto-select the first file (desktop only)
        if (window.innerWidth >= 768) {
            const firstGroup = tree.find(g => g.files && g.files.length > 0);
            if (firstGroup) {
                const firstFile = firstGroup.files[0];
                openKnowledgeFile(firstGroup.dir + '/' + firstFile.name, firstFile.title);
            }
        } else {
            document.getElementById('knowledge-content-placeholder').classList.add('hidden');
            document.getElementById('knowledge-content-viewer').classList.add('hidden');
        }
    }).catch(() => {});
}

function renderKnowledgeTree(tree, filter) {
    const container = document.getElementById('knowledge-tree');
    container.innerHTML = '';
    const lowerFilter = (filter || '').toLowerCase();

    tree.forEach(group => {
        const files = group.files.filter(f =>
            !lowerFilter || f.title.toLowerCase().includes(lowerFilter) || f.name.toLowerCase().includes(lowerFilter)
        );
        if (files.length === 0 && lowerFilter) return;

        const div = document.createElement('div');
        div.className = 'knowledge-tree-group open';

        const btn = document.createElement('button');
        btn.className = 'knowledge-tree-group-btn';
        btn.innerHTML = `<i class="fas fa-chevron-right chevron"></i><i class="fas fa-folder text-amber-400 text-[11px]"></i><span>${escapeHtml(group.dir)}</span><span class="ml-auto text-[10px] text-slate-400">${files.length}</span>`;
        btn.onclick = () => div.classList.toggle('open');
        div.appendChild(btn);

        const items = document.createElement('div');
        items.className = 'knowledge-tree-group-items';
        files.forEach(f => {
            const fbtn = document.createElement('button');
            const fpath = group.dir + '/' + f.name;
            fbtn.className = 'knowledge-tree-file' + (_knowledgeCurrentFile === fpath ? ' active' : '');
            fbtn.dataset.path = fpath;
            fbtn.innerHTML = `<i class="fas fa-file-lines text-[10px] text-slate-400"></i><span class="truncate">${escapeHtml(f.title)}</span>`;
            fbtn.onclick = () => openKnowledgeFile(fpath, f.title);
            items.appendChild(fbtn);
        });
        div.appendChild(items);
        container.appendChild(div);
    });
}

function filterKnowledgeTree(query) {
    renderKnowledgeTree(_knowledgeTreeData, query);
}

function resolveKnowledgePath(currentFilePath, relativeHref) {
    // currentFilePath: e.g. "concepts/mcp-protocol.md"
    // relativeHref: e.g. "../entities/openai.md"
    const parts = currentFilePath.split('/');
    parts.pop(); // remove filename, keep directory
    const segments = [...parts, ...relativeHref.split('/')];
    const resolved = [];
    for (const seg of segments) {
        if (seg === '..') resolved.pop();
        else if (seg !== '.' && seg !== '') resolved.push(seg);
    }
    return resolved.join('/');
}

function bindKnowledgeLinks(container, currentFilePath) {
    container.querySelectorAll('a').forEach(a => {
        const href = a.getAttribute('href');
        if (!href || !href.endsWith('.md')) return;
        // Skip absolute URLs
        if (/^https?:\/\//.test(href)) return;

        a.addEventListener('click', (e) => {
            e.preventDefault();
            const resolved = resolveKnowledgePath(currentFilePath, href);
            const linkTitle = a.textContent.trim() || resolved.replace(/\.md$/, '').split('/').pop();
            openKnowledgeFile(resolved, linkTitle);
        });
        a.style.cursor = 'pointer';
        a.classList.add('text-primary-500', 'hover:underline');
    });
}

function bindChatKnowledgeLinks(container) {
    if (!container) return;
    container.querySelectorAll('a').forEach(a => {
        const href = a.getAttribute('href');
        if (!href || !href.endsWith('.md')) return;
        if (/^https?:\/\//.test(href)) return;

        // Determine knowledge path
        let knowledgePath = null;
        if (href.startsWith('knowledge/')) {
            // Full path from workspace root: knowledge/concepts/moe.md
            knowledgePath = href.replace(/^knowledge\//, '');
        } else if (/^[a-z0-9_-]+\/[a-z0-9_.-]+\.md$/i.test(href)) {
            // Looks like category/file.md pattern without knowledge/ prefix
            knowledgePath = href;
        } else if (href.includes('/') && !href.startsWith('/')) {
            // Relative path like ../entities/deepseek.md — extract filename and search
            const filename = href.split('/').pop();
            knowledgePath = '__search__:' + filename;
        }
        if (!knowledgePath) return;

        a.addEventListener('click', (e) => {
            e.preventDefault();
            if (knowledgePath.startsWith('__search__:')) {
                const filename = knowledgePath.replace('__search__:', '');
                // Find the file in cached tree data
                const found = _findKnowledgeFileByName(filename);
                if (found) {
                    navigateTo('knowledge');
                    setTimeout(() => openKnowledgeFile(found.path, found.title), 100);
                }
            } else {
                navigateTo('knowledge');
                const linkTitle = a.textContent.trim() || knowledgePath.replace(/\.md$/, '').split('/').pop();
                setTimeout(() => openKnowledgeFile(knowledgePath, linkTitle), 100);
            }
        });
        a.style.cursor = 'pointer';
        a.classList.add('text-primary-500', 'hover:underline');
    });
}

function _findKnowledgeFileByName(filename) {
    for (const group of _knowledgeTreeData) {
        for (const f of group.files) {
            if (f.name === filename) {
                return { path: group.dir + '/' + f.name, title: f.title };
            }
        }
    }
    return null;
}

function openKnowledgeFile(path, title) {
    _knowledgeCurrentFile = path;
    // Update active state in tree via data-path
    document.querySelectorAll('.knowledge-tree-file').forEach(el => {
        el.classList.toggle('active', el.dataset.path === path);
    });

    // Immediately hide placeholder
    document.getElementById('knowledge-content-placeholder').classList.add('hidden');

    fetch(appendAgentQuery(`/api/knowledge/read?path=${encodeURIComponent(path)}`)).then(r => r.json()).then(data => {
        if (data.status !== 'success') return;
        const viewer = document.getElementById('knowledge-content-viewer');
        document.getElementById('knowledge-viewer-title').textContent = title;
        document.getElementById('knowledge-viewer-path').textContent = path;
        const bodyEl = document.getElementById('knowledge-viewer-body');
        bodyEl.innerHTML = renderMarkdown(data.content || '');
        viewer.classList.remove('hidden');
        applyHighlighting(viewer);
        bindKnowledgeLinks(bodyEl, path);

        // Mobile: hide sidebar, show content
        if (window.innerWidth < 768) {
            document.getElementById('knowledge-sidebar').classList.add('hidden');
        }
    }).catch(() => {});
}

function knowledgeMobileBack() {
    document.getElementById('knowledge-sidebar').classList.remove('hidden');
    document.getElementById('knowledge-content-viewer').classList.add('hidden');
}

function switchKnowledgeTab(tab) {
    document.querySelectorAll('.knowledge-tab').forEach(el => el.classList.remove('active'));
    document.getElementById('knowledge-tab-' + tab).classList.add('active');

    const docsPanel = document.getElementById('knowledge-panel-docs');
    const graphPanel = document.getElementById('knowledge-panel-graph');

    if (tab === 'docs') {
        docsPanel.classList.remove('hidden');
        graphPanel.classList.add('hidden');
    } else {
        docsPanel.classList.add('hidden');
        graphPanel.classList.remove('hidden');
        if (!_knowledgeGraphLoaded) {
            loadKnowledgeGraph();
        }
    }
}

function loadKnowledgeGraph() {
    _knowledgeGraphLoaded = true;
    const container = document.getElementById('knowledge-graph-container');
    container.innerHTML = '';

    fetch(appendAgentQuery('/api/knowledge/graph')).then(r => r.json()).then(data => {
        const nodes = data.nodes || [];
        const links = data.links || [];
        if (nodes.length === 0) {
            container.innerHTML = `<div class="flex flex-col items-center justify-center h-full text-slate-400"><i class="fas fa-diagram-project text-3xl mb-3 opacity-40"></i><p class="text-sm">${t('knowledge_empty_hint')}</p></div>`;
            return;
        }
        renderKnowledgeGraph(container, nodes, links);
    }).catch(() => {
        container.innerHTML = '<div class="flex items-center justify-center h-full text-slate-400 text-sm">Failed to load graph</div>';
    });
}

function renderKnowledgeGraph(container, nodes, links) {
    const width = container.clientWidth;
    const height = container.clientHeight || 600;

    const categories = [...new Set(nodes.map(n => n.category))];
    const colorScale = d3.scaleOrdinal(d3.schemeTableau10).domain(categories);

    // Connection count for sizing
    const connCount = {};
    nodes.forEach(n => connCount[n.id] = 0);
    links.forEach(l => {
        connCount[l.source] = (connCount[l.source] || 0) + 1;
        connCount[l.target] = (connCount[l.target] || 0) + 1;
    });

    const svg = d3.select(container)
        .append('svg')
        .attr('width', width)
        .attr('height', height);

    const g = svg.append('g');

    // Zoom with adaptive label visibility
    let currentZoomScale = 1;
    const zoom = d3.zoom()
        .scaleExtent([0.2, 5])
        .on('zoom', (event) => {
            g.attr('transform', event.transform);
            currentZoomScale = event.transform.k;
            updateLabelVisibility();
        });
    svg.call(zoom);

    function updateLabelVisibility() {
        if (!label) return;
        if (currentZoomScale < 0.8) {
            label.attr('opacity', 0);
        } else {
            const baseFontSize = Math.min(12, 10 / Math.max(currentZoomScale * 0.7, 0.5));
            label.attr('opacity', 1).attr('font-size', baseFontSize);
        }
    }

    const simulation = d3.forceSimulation(nodes)
        .force('link', d3.forceLink(links).id(d => d.id).distance(90))
        .force('charge', d3.forceManyBody().strength(-180))
        .force('center', d3.forceCenter(width / 2, height / 2))
        .force('x', d3.forceX(width / 2).strength(0.06))
        .force('y', d3.forceY(height / 2).strength(0.06))
        .force('collision', d3.forceCollide().radius(d => getNodeRadius(d) + 30));

    function getNodeRadius(d) {
        return Math.max(5, Math.min(16, 5 + (connCount[d.id] || 0) * 2));
    }

    const link = g.append('g')
        .selectAll('line')
        .data(links)
        .join('line')
        .attr('stroke', '#94a3b8')
        .attr('stroke-opacity', 0.3)
        .attr('stroke-width', 1);

    const node = g.append('g')
        .selectAll('circle')
        .data(nodes)
        .join('circle')
        .attr('r', d => getNodeRadius(d))
        .attr('fill', d => colorScale(d.category))
        .attr('stroke', '#fff')
        .attr('stroke-width', 1.5)
        .style('cursor', 'pointer')
        .call(d3.drag()
            .on('start', (event, d) => { if (!event.active) simulation.alphaTarget(0.3).restart(); d.fx = d.x; d.fy = d.y; })
            .on('drag', (event, d) => { d.fx = event.x; d.fy = event.y; })
            .on('end', (event, d) => { if (!event.active) simulation.alphaTarget(0); d.fx = null; d.fy = null; })
        );

    const label = g.append('g')
        .selectAll('text')
        .data(nodes)
        .join('text')
        .text(d => d.label.length > 15 ? d.label.slice(0, 14) + '…' : d.label)
        .attr('font-size', 9)
        .attr('dx', d => getNodeRadius(d) + 4)
        .attr('dy', 3)
        .attr('fill', '#64748b')
        .style('pointer-events', 'none');

    // Tooltip
    const tooltip = document.createElement('div');
    tooltip.className = 'knowledge-graph-tooltip';
    container.style.position = 'relative';
    container.appendChild(tooltip);

    node.on('mouseover', (event, d) => {
        tooltip.textContent = d.label + ' (' + d.category + ')';
        tooltip.style.opacity = '1';
        tooltip.style.left = (event.offsetX + 12) + 'px';
        tooltip.style.top = (event.offsetY - 8) + 'px';
        // Highlight connections
        link.attr('stroke-opacity', l => (l.source.id === d.id || l.target.id === d.id) ? 0.8 : 0.1);
        node.attr('opacity', n => n.id === d.id || links.some(l => (l.source.id === d.id && l.target.id === n.id) || (l.target.id === d.id && l.source.id === n.id)) ? 1 : 0.2);
        label.attr('opacity', n => n.id === d.id || links.some(l => (l.source.id === d.id && l.target.id === n.id) || (l.target.id === d.id && l.source.id === n.id)) ? 1 : 0.1);
    }).on('mousemove', (event) => {
        tooltip.style.left = (event.offsetX + 12) + 'px';
        tooltip.style.top = (event.offsetY - 8) + 'px';
    }).on('mouseout', () => {
        tooltip.style.opacity = '0';
        link.attr('stroke-opacity', 0.3);
        node.attr('opacity', 1);
        label.attr('opacity', 1);
    }).on('click', (event, d) => {
        // Switch to docs tab and open the file
        switchKnowledgeTab('docs');
        openKnowledgeFile(d.id, d.label);
    });

    simulation.on('tick', () => {
        link.attr('x1', d => d.source.x).attr('y1', d => d.source.y)
            .attr('x2', d => d.target.x).attr('y2', d => d.target.y);
        node.attr('cx', d => d.x).attr('cy', d => d.y);
        label.attr('x', d => d.x).attr('y', d => d.y);
    });

    // Auto fit-to-view when simulation settles
    simulation.on('end', () => {
        const pad = 16;
        let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
        nodes.forEach(n => {
            if (n.x < x0) x0 = n.x;
            if (n.y < y0) y0 = n.y;
            if (n.x > x1) x1 = n.x;
            if (n.y > y1) y1 = n.y;
        });
        const bw = x1 - x0 + pad * 2;
        const bh = y1 - y0 + pad * 2;
        if (bw > 0 && bh > 0) {
            const scale = Math.min(width / bw, height / bh, 4);
            const tx = width / 2 - (x0 + x1) / 2 * scale;
            const ty = height / 2 - (y0 + y1) / 2 * scale;
            svg.transition().duration(500).call(
                zoom.transform, d3.zoomIdentity.translate(tx, ty).scale(scale)
            );
        }
    });

    // Legend
    const legendDiv = document.createElement('div');
    legendDiv.className = 'knowledge-graph-legend';
    categories.forEach(cat => {
        const item = document.createElement('span');
        item.className = 'knowledge-graph-legend-item';
        item.innerHTML = `<span class="knowledge-graph-legend-dot" style="background:${colorScale(cat)}"></span>${escapeHtml(cat)}`;
        legendDiv.appendChild(item);
    });
    container.appendChild(legendDiv);
}

// =====================================================================
// Authentication
// =====================================================================
function toggleLoginPassword() {
    const input = document.getElementById('login-password');
    const icon = document.querySelector('#login-toggle-pwd i');
    if (input.type === 'password') {
        input.type = 'text';
        icon.classList.replace('fa-eye', 'fa-eye-slash');
    } else {
        input.type = 'password';
        icon.classList.replace('fa-eye-slash', 'fa-eye');
    }
}
window.toggleLoginPassword = toggleLoginPassword;

function showLoginScreen() {
    const overlay = document.getElementById('login-overlay');
    if (!overlay) return;
    overlay.classList.remove('hidden');
    document.getElementById('app').classList.add('hidden');

    const subtitle = document.getElementById('login-subtitle');
    const loginBtn = document.getElementById('login-btn');
    if (currentLang === 'en') {
        subtitle.textContent = 'Enter password to access the console';
        loginBtn.textContent = 'Login';
    } else {
        subtitle.textContent = '请输入密码以访问控制台';
        loginBtn.textContent = '登录';
    }

    const form = document.getElementById('login-form');
    const pwdInput = document.getElementById('login-password');
    pwdInput.focus();

    form.onsubmit = function(e) {
        e.preventDefault();
        const pwd = pwdInput.value;
        if (!pwd) return;
        const btn = document.getElementById('login-btn');
        const errEl = document.getElementById('login-error');
        btn.disabled = true;
        errEl.classList.add('hidden');

        fetch('/auth/login', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({password: pwd})
        }).then(r => r.json()).then(data => {
            if (data.status === 'success') {
                overlay.classList.add('hidden');
                document.getElementById('app').classList.remove('hidden');
                initApp();
            } else {
                errEl.textContent = currentLang === 'zh' ? '密码错误' : 'Wrong password';
                errEl.classList.remove('hidden');
                pwdInput.value = '';
                pwdInput.focus();
            }
            btn.disabled = false;
        }).catch(() => {
            errEl.textContent = currentLang === 'zh' ? '网络错误，请重试' : 'Network error, please retry';
            errEl.classList.remove('hidden');
            btn.disabled = false;
        });
        return false;
    };
}

// Intercept 401 responses globally to show login screen on session expiry
const _originalFetch = window.fetch;
window.fetch = function(...args) {
    return _originalFetch.apply(this, args).then(response => {
        if (response.status === 401) {
            const url = typeof args[0] === 'string' ? args[0] : (args[0]?.url || '');
            if (!url.startsWith('/auth/')) {
                showLoginScreen();
            }
        }
        return response;
    });
};

function initApp() {
    applyI18n();
    _applyInputTooltips();
    _restoreSessionPanel();

    fetch(appendAgentQuery('/api/knowledge/list')).then(r => r.json()).then(data => {
        if (data.status === 'success') _knowledgeTreeData = data.tree || [];
    }).catch(() => {});

    fetch('/api/version').then(r => r.json()).then(data => {
        APP_VERSION = `v${data.version}`;
        document.getElementById('sidebar-version').textContent = `CowAgent ${APP_VERSION}`;
    }).catch(() => {
        document.getElementById('sidebar-version').textContent = 'CowAgent';
    });
    chatInput.focus();
}

// =====================================================================
// Initialization
// =====================================================================
applyTheme();
applyI18n();

fetch('/auth/check').then(r => r.json()).then(data => {
    if (data.auth_required && !data.authenticated) {
        showLoginScreen();
    } else {
        initApp();
    }
}).catch(() => {
    initApp();
});

requestAnimationFrame(() => {
    document.body.classList.add('transition-colors', 'duration-200');
});
