import type {
  AgentItem,
  BindingItem,
  ChannelItem,
  ChannelConfigItem,
  ChannelTypeItem,
  ChatAttachment,
  McpTestResult,
  McpServerItem,
  McpToolItem,
  RuntimeScope,
  SessionItem,
  SkillItem,
  TenantItem,
  TenantUserItem,
  ToolItem,
  UploadedFileResponse,
  UsageRecordItem,
  UsageSummary,
  WeixinQrInfo,
  AuthUser,
  ModelConfigItem,
} from '../types';
import { buildQuery, requestJson, scopeBody, scopeQuery } from './http';

export const api = {
  authCheck: () => requestJson<{
    status: string;
    auth_required: boolean;
    authenticated?: boolean;
    bootstrap_required?: boolean;
    platform_bootstrap_required?: boolean;
    auth_mode?: string;
    user?: AuthUser | null;
  }>('/auth/check'),
  login: (payload: { account?: string; tenant_id?: string; user_id?: string; password: string }) => requestJson('/auth/login', {
    method: 'POST',
    body: JSON.stringify(payload),
  }),
  registerTenant: (payload: Record<string, any>) => requestJson('/auth/register', {
    method: 'POST',
    body: JSON.stringify(payload),
  }),
  registerPlatformAdmin: (payload: Record<string, any>) => requestJson('/auth/platform-register', {
    method: 'POST',
    body: JSON.stringify(payload),
  }),
  logout: () => requestJson('/auth/logout', { method: 'POST' }),

  getConfig: () => requestJson<Record<string, any>>('/config'),
  updateConfig: (updates: Record<string, any>) => requestJson('/config', {
    method: 'POST',
    body: JSON.stringify({ updates }),
  }),

  listTools: () => requestJson<{ status: string; tools: ToolItem[] }>('/api/tools'),
  listSkills: (scope: RuntimeScope) => requestJson<{ status: string; skills: SkillItem[] }>(`/api/skills${buildQuery(scopeQuery(scope))}`),
  toggleSkill: (scope: RuntimeScope, name: string, action: 'open' | 'close') => requestJson('/api/skills', {
    method: 'POST',
    body: JSON.stringify({ name, action, ...scopeBody(scope) }),
  }),
  deleteSkill: (scope: RuntimeScope, name: string) => requestJson('/api/skills', {
    method: 'POST',
    body: JSON.stringify({ name, action: 'delete', ...scopeBody(scope) }),
  }),

  listAgentsSimple: () => requestJson<{ status: string; agents: AgentItem[] }>('/api/agents'),
  listAgents: (tenantId = '') => requestJson<{ status: string; agents: AgentItem[] }>(`/api/platform/agents${buildQuery({ tenant_id: tenantId })}`),
  createAgent: (payload: Record<string, any>) => requestJson('/api/platform/agents', { method: 'POST', body: JSON.stringify(payload) }),
  getAgentDetail: (tenantId: string, agentId: string) => requestJson<{ status: string; agent: AgentItem }>(`/api/platform/agents/${encodeURIComponent(agentId)}${buildQuery({ tenant_id: tenantId })}`),
  updateAgent: (agentId: string, payload: Record<string, any>) => requestJson(`/api/platform/agents/${encodeURIComponent(agentId)}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  }),
  deleteAgent: (tenantId: string, agentId: string) => requestJson(`/api/platform/agents/${encodeURIComponent(agentId)}${buildQuery({ tenant_id: tenantId })}`, { method: 'DELETE' }),

  listBindingsSimple: () => requestJson<{ status: string; bindings: BindingItem[] }>('/api/bindings?channel_type=web'),
  listBindings: (tenantId = '', channelType = '', channelConfigId = '') => requestJson<{ status: string; bindings: BindingItem[] }>(`/api/platform/bindings${buildQuery({ tenant_id: tenantId, channel_type: channelType, channel_config_id: channelConfigId })}`),
  createBinding: (payload: Record<string, any>) => requestJson('/api/platform/bindings', { method: 'POST', body: JSON.stringify(payload) }),
  getBindingDetail: (tenantId: string, bindingId: string) => requestJson<{ status: string; binding: BindingItem }>(`/api/platform/bindings/${encodeURIComponent(bindingId)}${buildQuery({ tenant_id: tenantId })}`),
  updateBinding: (bindingId: string, payload: Record<string, any>) => requestJson(`/api/platform/bindings/${encodeURIComponent(bindingId)}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  }),
  deleteBinding: (tenantId: string, bindingId: string) => requestJson(`/api/platform/bindings/${encodeURIComponent(bindingId)}${buildQuery({ tenant_id: tenantId })}`, { method: 'DELETE' }),
  listUsage: (tenantId = '', agentId = '', day = '', limit = 100) => requestJson<{ status: string; usage: UsageRecordItem[] }>(
    `/api/platform/usage${buildQuery({ tenant_id: tenantId, agent_id: agentId, day, limit })}`,
  ),
  getCostSummary: (tenantId = '', agentId = '', day = '') => requestJson<{ status: string; summary: UsageSummary }>(
    `/api/platform/costs${buildQuery({ tenant_id: tenantId, agent_id: agentId, day })}`,
  ),

  listTenants: () => requestJson<{ status: string; tenants: TenantItem[] }>('/api/platform/tenants'),
  createTenant: (payload: Record<string, any>) => requestJson('/api/platform/tenants', { method: 'POST', body: JSON.stringify(payload) }),
  updateTenant: (tenantId: string, payload: Record<string, any>) => requestJson(`/api/platform/tenants/${encodeURIComponent(tenantId)}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  }),
  listPlatformTenants: () => requestJson<{ status: string; tenants: TenantItem[] }>('/api/platform/admin/tenants'),
  createPlatformTenant: (payload: Record<string, any>) => requestJson('/api/platform/admin/tenants', { method: 'POST', body: JSON.stringify(payload) }),
  updatePlatformTenant: (tenantId: string, payload: Record<string, any>) => requestJson(`/api/platform/admin/tenants/${encodeURIComponent(tenantId)}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  }),
  deletePlatformTenant: (tenantId: string) => requestJson(`/api/platform/admin/tenants/${encodeURIComponent(tenantId)}`, { method: 'DELETE' }),

  listPlatformModels: () => requestJson<{ status: string; models: ModelConfigItem[]; providers?: Array<{ provider: string; bot_type: string }> }>('/api/platform/admin/models'),
  createPlatformModel: (payload: Record<string, any>) => requestJson('/api/platform/admin/models', { method: 'POST', body: JSON.stringify(payload) }),
  updatePlatformModel: (modelConfigId: string, payload: Record<string, any>) => requestJson(`/api/platform/admin/models/${encodeURIComponent(modelConfigId)}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  }),
  deletePlatformModel: (modelConfigId: string) => requestJson(`/api/platform/admin/models/${encodeURIComponent(modelConfigId)}`, { method: 'DELETE' }),
  listAvailableModels: (tenantId = '') => requestJson<{ status: string; models: ModelConfigItem[] }>(`/api/platform/models/available${buildQuery({ tenant_id: tenantId })}`),
  listTenantModels: (tenantId = '') => requestJson<{ status: string; models: ModelConfigItem[] }>(`/api/platform/tenant-models${buildQuery({ tenant_id: tenantId })}`),
  createTenantModel: (payload: Record<string, any>) => requestJson('/api/platform/tenant-models', { method: 'POST', body: JSON.stringify(payload) }),
  updateTenantModel: (modelConfigId: string, payload: Record<string, any>) => requestJson(`/api/platform/tenant-models/${encodeURIComponent(modelConfigId)}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  }),
  deleteTenantModel: (modelConfigId: string) => requestJson(`/api/platform/tenant-models/${encodeURIComponent(modelConfigId)}`, { method: 'DELETE' }),

  listChannelConfigs: (tenantId = '', channelType = '') => requestJson<{ status: string; channel_configs: ChannelConfigItem[]; channel_types: ChannelTypeItem[] }>(
    `/api/platform/channel-configs${buildQuery({ tenant_id: tenantId, channel_type: channelType })}`,
  ),
  createChannelConfig: (payload: Record<string, any>) => requestJson('/api/platform/channel-configs', { method: 'POST', body: JSON.stringify(payload) }),
  updateChannelConfig: (channelConfigId: string, payload: Record<string, any>) => requestJson(`/api/platform/channel-configs/${encodeURIComponent(channelConfigId)}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  }),
  deleteChannelConfig: (tenantId: string, channelConfigId: string) => requestJson(`/api/platform/channel-configs/${encodeURIComponent(channelConfigId)}${buildQuery({ tenant_id: tenantId })}`, { method: 'DELETE' }),

  getTenantUserMeta: () => requestJson<{ status: string; roles: string[]; statuses: string[] }>('/api/platform/tenant-user-meta'),
  listTenantUsers: (tenantId = '', role = '', status = '') => requestJson<{ status: string; tenant_users: TenantUserItem[] }>(
    `/api/platform/tenant-users${buildQuery({ tenant_id: tenantId, role, status })}`,
  ),
  createTenantUser: (payload: Record<string, any>) => requestJson('/api/platform/tenant-users', { method: 'POST', body: JSON.stringify(payload) }),
  updateTenantUser: (tenantId: string, userId: string, payload: Record<string, any>) => requestJson(`/api/platform/tenant-users/${encodeURIComponent(tenantId)}/${encodeURIComponent(userId)}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  }),
  deleteTenantUser: (tenantId: string, userId: string) => requestJson(`/api/platform/tenant-users/${encodeURIComponent(tenantId)}/${encodeURIComponent(userId)}`, { method: 'DELETE' }),
  listTenantIdentities: (tenantId = '', userId = '', channelType = '') => requestJson<{ status: string; identities: any[] }>(
    `/api/platform/tenant-user-identities${buildQuery({ tenant_id: tenantId, user_id: userId, channel_type: channelType })}`,
  ),
  bindTenantIdentity: (payload: Record<string, any>) => requestJson('/api/platform/tenant-user-identities', {
    method: 'POST',
    body: JSON.stringify(payload),
  }),
  deleteTenantIdentity: (tenantId: string, channelType: string, externalUserId: string) => requestJson(
    `/api/platform/tenant-user-identities/${encodeURIComponent(tenantId)}/${encodeURIComponent(channelType)}/${encodeURIComponent(externalUserId)}`,
    { method: 'DELETE' },
  ),

  listMcpServers: (agentId: string, tenantId = '') => requestJson<{ status: string; servers: McpServerItem[] }>(`/api/mcp/servers${buildQuery({ agent_id: agentId, tenant_id: tenantId })}`),
  testMcpServer: (payload: Record<string, any>) => requestJson<McpTestResult>('/api/mcp/servers/test', {
    method: 'POST',
    body: JSON.stringify(payload),
  }),
  listMcpServerTools: (serverName: string, agentId?: string, tenantId = '') => requestJson<{ status: string; tools: McpToolItem[] }>(`/api/mcp/servers/${encodeURIComponent(serverName)}/tools${buildQuery({ agent_id: agentId || '', tenant_id: tenantId })}`),

  listChannels: () => requestJson<{ status: string; channels: ChannelItem[] }>('/api/channels'),
  channelAction: (payload: Record<string, any>) => requestJson('/api/channels', { method: 'POST', body: JSON.stringify(payload) }),
  weixinQrGet: (channelConfigId = '') => requestJson<WeixinQrInfo>(`/api/weixin/qrlogin${buildQuery({ channel_config_id: channelConfigId })}`),
  weixinQrPost: (action: 'poll' | 'refresh', channelConfigId = '') => requestJson<WeixinQrInfo>('/api/weixin/qrlogin', {
    method: 'POST',
    body: JSON.stringify({ action, channel_config_id: channelConfigId }),
  }),

  listMemory: (scope: RuntimeScope, category = 'memory', page = 1, pageSize = 50) => requestJson<Record<string, any>>(
    `/api/memory${buildQuery({ ...scopeQuery(scope), category, page, page_size: pageSize })}`,
  ),
  memoryContent: (scope: RuntimeScope, filename: string, category = 'memory') => requestJson<Record<string, any>>(
    `/api/memory/content${buildQuery({ ...scopeQuery(scope), filename, category })}`,
  ),
  listKnowledge: (scope: RuntimeScope) => requestJson<Record<string, any>>(`/api/knowledge/list${buildQuery(scopeQuery(scope))}`),
  readKnowledge: (scope: RuntimeScope, path: string) => requestJson<Record<string, any>>(`/api/knowledge/read${buildQuery({ ...scopeQuery(scope), path })}`),
  graphKnowledge: (scope: RuntimeScope) => requestJson<Record<string, any>>(`/api/knowledge/graph${buildQuery(scopeQuery(scope))}`),

  listTasks: (scope: RuntimeScope) => requestJson<{ status: string; tasks: any[] }>(`/api/scheduler${buildQuery(scopeQuery(scope))}`),

  listSessions: (scope: RuntimeScope, page = 1, pageSize = 50) => requestJson<{ status: string; sessions: SessionItem[]; has_more?: boolean }>(
    `/api/sessions${buildQuery({ ...scopeQuery(scope), page, page_size: pageSize })}`,
  ),
  deleteSession: (scope: RuntimeScope, sessionId: string) => requestJson(`/api/sessions/${encodeURIComponent(sessionId)}${buildQuery(scopeQuery(scope))}`, { method: 'DELETE' }),
  renameSession: (scope: RuntimeScope, sessionId: string, title: string) => requestJson(`/api/sessions/${encodeURIComponent(sessionId)}`, {
    method: 'PUT',
    body: JSON.stringify({ ...scopeBody(scope), title }),
  }),
  clearContext: (scope: RuntimeScope, sessionId: string) => requestJson(`/api/sessions/${encodeURIComponent(sessionId)}/clear_context${buildQuery(scopeQuery(scope))}`, { method: 'POST' }),
  generateSessionTitle: (scope: RuntimeScope, sessionId: string, userMessage: string, assistantReply = '') => requestJson(`/api/sessions/${encodeURIComponent(sessionId)}/generate_title`, {
    method: 'POST',
    body: JSON.stringify({ ...scopeBody(scope), user_message: userMessage, assistant_reply: assistantReply }),
  }),
  history: (scope: RuntimeScope, sessionId: string, page = 1, pageSize = 50) => requestJson<{ status: string; messages: any[]; has_more?: boolean; context_start_seq?: number }>(
    `/api/history${buildQuery({ ...scopeQuery(scope), session_id: sessionId, page, page_size: pageSize })}`,
  ),

  sendMessage: (scope: RuntimeScope, payload: Record<string, any>) => requestJson<{ status: string; request_id: string; stream: boolean }>('/message', {
    method: 'POST',
    body: JSON.stringify({ ...payload, ...scopeBody(scope) }),
  }),
  pollMessage: (scope: RuntimeScope, sessionId: string) => requestJson<{ status: string; has_content: boolean; content?: string; request_id?: string; timestamp?: number }>('/poll', {
    method: 'POST',
    body: JSON.stringify({ ...scopeBody(scope), session_id: sessionId }),
  }),
  uploadFile: async (scope: RuntimeScope, sessionId: string, file: File): Promise<UploadedFileResponse> => {
    const formData = new FormData();
    formData.append('session_id', sessionId);
    formData.append('file', file);
    const body = scopeBody(scope);
    Object.entries(body).forEach(([key, value]) => formData.append(key, value));

    const res = await fetch('/upload', {
      method: 'POST',
      body: formData,
      credentials: 'same-origin',
    });
    const data = (await res.json()) as UploadedFileResponse;
    if (!res.ok || data.status !== 'success') {
      throw new Error(data.message || '上传失败');
    }
    return data;
  },
};

export function formatAgentPayload(input: Partial<AgentItem>): Record<string, any> {
  return {
    tenant_id: input.tenant_id || 'default',
    agent_id: input.agent_id || undefined,
    name: input.name || '',
    model: input.model || '',
    model_config_id: input.model_config_id || '',
    system_prompt: input.system_prompt || '',
    tools: input.tools || [],
    skills: input.skills || [],
    knowledge_enabled: Boolean(input.knowledge_enabled),
    mcp_servers: input.mcp_servers || {},
  };
}

export function formatBindingPayload(input: Partial<BindingItem>): Record<string, any> {
  return {
    tenant_id: input.tenant_id || 'default',
    binding_id: input.binding_id || '',
    name: input.name || '',
    channel_type: input.channel_type || 'web',
    channel_config_id: input.channel_config_id || '',
    agent_id: input.agent_id || '',
    enabled: input.enabled ?? true,
    metadata: input.metadata || {},
  };
}

export function asAttachment(item: UploadedFileResponse): ChatAttachment {
  return {
    file_path: item.file_path,
    file_name: item.file_name,
    file_type: item.file_type,
    preview_url: item.preview_url,
  };
}
