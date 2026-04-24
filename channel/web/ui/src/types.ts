import type { ThoughtChainItemType } from '@ant-design/x';

export interface ApiResponse<T = unknown> {
  status: 'success' | 'error';
  message?: string;
  data?: T;
  [key: string]: unknown;
}

export interface RuntimeScope {
  agentId: string;
  bindingId: string;
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
  system_prompt?: string;
  tools?: string[];
  skills?: string[];
  knowledge_enabled?: boolean;
  mcp_servers?: Record<string, { command?: string; args?: string[]; env?: Record<string, string> }>;
}

export interface BindingItem {
  tenant_id: string;
  binding_id: string;
  name: string;
  channel_type: string;
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

export interface SkillItem {
  name: string;
  description?: string;
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
  type: 'text' | 'secret' | 'number' | 'bool';
  value?: string | number | boolean;
  default?: string | number | boolean;
}

export interface ChannelItem {
  name: string;
  label?: {
    zh?: string;
    en?: string;
  };
  icon?: string;
  color?: string;
  active: boolean;
  login_status?: string;
  fields: ChannelField[];
}

export interface WeixinQrInfo {
  status: 'success' | 'error';
  qrcode_url?: string;
  qr_image?: string;
  qr_status?: string;
  source?: string;
  bot_id?: string;
  message?: string;
}

export interface McpServerItem {
  name: string;
  command: string;
  args: string[];
  env: Record<string, string>;
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
