import type { ThoughtChainItemType } from '@ant-design/x';

export interface ApiResponse<T = unknown> {
  status: 'success' | 'error';
  message?: string;
  data?: T;
  [key: string]: unknown;
}

export interface RuntimeScope {
  tenantId: string;
  agentId: string;
  bindingId: string;
}

export interface AuthUser {
  tenant_id?: string;
  user_id: string;
  role: string;
  principal_type?: 'tenant' | 'platform';
  tenant_name?: string;
  user_name?: string;
  account?: string;
  expires_at?: number;
}

export interface ChatAttachment {
  file_path: string;
  file_name: string;
  file_type: 'image' | 'video' | 'file';
  preview_url?: string;
}

export interface UploadedFileResponse {
  status: 'success' | 'error';
  file_path: string;
  file_name: string;
  file_type: 'image' | 'video' | 'file';
  preview_url: string;
  message?: string;
}

export interface ChatMessageRecord {
  key: string;
  role: 'user' | 'assistant' | 'system';
  createdAt: number;
  content: string | AssistantBubbleContent;
}

export interface AssistantMedia {
  type: 'image' | 'video' | 'file';
  url: string;
  fileName?: string;
}

export interface AssistantBubbleContent {
  text: string;
  steps: AssistantStep[];
  media: AssistantMedia[];
  streaming: boolean;
}

export interface AssistantStep {
  key: string;
  kind: 'reasoning' | 'tool' | 'phase' | 'output' | 'status';
  title: string;
  description?: string;
  status: NonNullable<ThoughtChainItemType['status']>;
  markdown?: string;
  inputMarkdown?: string;
  outputMarkdown?: string;
  footer?: string;
  toolName?: string;
  startedAt?: number;
  durationSeconds?: number;
}

export interface SessionItem {
  session_id: string;
  title?: string;
  updated_at?: number;
  created_at?: number;
  last_active?: number;
  msg_count?: number;
}

export interface AgentItem {
  tenant_id: string;
  agent_id: string;
  name: string;
  model: string;
  model_config_id?: string;
  system_prompt?: string;
  tools?: string[];
  skills?: string[];
  knowledge_enabled?: boolean;
  mcp_servers?: Record<string, { command?: string; args?: string[]; env?: Record<string, string>; enabled?: boolean }>;
}

export interface BindingItem {
  tenant_id: string;
  binding_id: string;
  name: string;
  channel_type: string;
  channel_config_id?: string;
  agent_id: string;
  enabled?: boolean;
  metadata?: Record<string, unknown>;
}

export interface TenantItem {
  tenant_id: string;
  name: string;
  status: string;
  metadata?: Record<string, unknown>;
}

export interface TenantUserItem {
  tenant_id: string;
  user_id: string;
  name: string;
  role: string;
  status: string;
  metadata?: Record<string, unknown>;
}

export interface ModelConfigItem {
  model_config_id: string;
  scope: 'platform' | 'tenant';
  tenant_id?: string;
  provider: string;
  model_name: string;
  display_name?: string;
  api_base?: string;
  enabled: boolean;
  is_public: boolean;
  api_key_set?: boolean;
  api_key_masked?: string;
  metadata?: Record<string, unknown>;
}

export interface ModelProviderOption {
  provider: string;
  label: string;
  bot_type: string;
  models: string[];
  custom?: boolean;
  requires_api_base?: boolean;
  platform_configurable?: boolean;
  tenant_configurable?: boolean;
}

export interface SkillItem {
  name: string;
  description?: string;
  source?: 'builtin' | 'custom' | string;
  display_name?: string;
  category?: string;
  enabled?: boolean;
  open?: boolean;
  active?: boolean;
  is_open?: boolean;
  [key: string]: unknown;
}

export interface ToolItem {
  name: string;
  description?: string;
}

export interface ChannelField {
  key: string;
  label: string;
  type: 'text' | 'secret' | 'number' | 'bool' | 'list';
  value?: string | number | boolean | string[];
  default?: string | number | boolean | string[];
}

export interface ChannelTypeItem {
  channel_type: string;
  label: string;
  managed_runtime?: boolean;
  webhook_path_prefix?: string;
  fields: ChannelField[];
}

export interface ChannelConfigItem {
  tenant_id: string;
  channel_config_id: string;
  name: string;
  channel_type: string;
  label?: string;
  enabled: boolean;
  managed_runtime?: boolean;
  webhook_path?: string;
  config?: Record<string, string | number | boolean | string[]>;
  fields?: Array<ChannelField & { secret_set?: boolean }>;
  metadata?: Record<string, unknown>;
}

export interface WeixinQrInfo {
  status: 'success' | 'error';
  qrcode_url?: string;
  qr_image?: string;
  qr_status?: string;
  source?: string;
  bot_id?: string;
  channel_config_id?: string;
  message?: string;
}

export interface McpServerItem {
  name: string;
  command: string;
  args: string[];
  env: Record<string, string>;
  enabled?: boolean;
}

export interface McpToolItem {
  name: string;
  description?: string;
  inputSchema?: Record<string, unknown>;
}

export interface McpTestResult {
  status: 'success' | 'error';
  message?: string;
  tools?: McpToolItem[];
  [key: string]: unknown;
}

export interface UsageRecordItem {
  event_id: string;
  request_id: string;
  tenant_id: string;
  agent_id: string;
  binding_id?: string;
  session_id?: string;
  channel_type?: string;
  model?: string;
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  token_source?: string;
  request_count: number;
  tool_call_count: number;
  mcp_call_count: number;
  tool_error_count: number;
  tool_execution_time_ms: number;
  estimated_cost: number;
  created_at: string;
  metadata?: Record<string, unknown>;
}

export interface UsageSummary {
  tenant_id?: string;
  agent_id?: string;
  day?: string;
  request_count: number;
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  provider_request_count: number;
  estimated_request_count: number;
  tool_call_count: number;
  mcp_call_count: number;
  tool_error_count: number;
  tool_execution_time_ms: number;
  estimated_cost: number;
}
