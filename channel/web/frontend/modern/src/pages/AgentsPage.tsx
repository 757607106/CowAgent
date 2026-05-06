import {
  ApiOutlined,
  BuildOutlined,
  EditOutlined,
  MessageOutlined,
  PlusOutlined,
  ReloadOutlined,
  SearchOutlined,
  SettingOutlined,
  ToolOutlined,
  DeleteOutlined,
} from '@ant-design/icons';
import {
  Avatar,
  Button,
  Empty,
  Form,
  Input,
  Modal,
  Popover,
  Select,
  Switch,
  Tag,
  Typography,
  message,
} from 'antd';
import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ConsoleFilterBar, ConsolePage, MetricStrip, PageToolbar } from '../components/console';
import { EmployeeCard } from '../components/EmployeeCard';
import { displayAgentName, useRuntimeScope } from '../context/runtime';
import { api, formatAgentPayload } from '../services/api';
import type { AgentItem, ModelConfigItem, SkillItem, TenantItem, ToolItem } from '../types';
import { AGENT_AVATAR_OPTIONS, DEFAULT_AGENT_AVATAR_KEY, avatarOptionByKey, agentAvatarOption } from '../utils/avatar';

interface AgentFormValues {
  tenant_id: string;
  agent_id: string;
  name: string;
  position: string;
  role_intro: string;
  avatar_key: string;
  model_config_id: string;
  system_prompt: string;
  tools: string[];
  skills: string[];
  knowledge_enabled: boolean;
}

type AgentBadgeStatus = 'success' | 'processing' | 'default' | 'warning' | 'error';

const LEGACY_MODEL_PREFIX = 'legacy-model:';
const DEFAULT_AGENT_POSITION = 'AI 业务专员';

function isDefaultAgent(agent: AgentItem | null | undefined): boolean {
  return agent?.agent_id === 'default';
}

function inheritsDefaultTools(agent: AgentItem | null | undefined): boolean {
  return isDefaultAgent(agent) && !(agent?.tools || []).length;
}

function inheritsDefaultSkills(agent: AgentItem | null | undefined): boolean {
  return isDefaultAgent(agent) && !(agent?.skills || []).length;
}

function effectiveToolNames(agent: AgentItem, availableTools: ToolItem[]): string[] {
  if (inheritsDefaultTools(agent)) return availableTools.map((tool) => tool.name);
  return agent.tools || [];
}

function effectiveSkillNames(agent: AgentItem, availableSkills: SkillItem[]): string[] {
  if (inheritsDefaultSkills(agent)) return availableSkills.map((skill) => skill.name);
  return agent.skills || [];
}

function agentInitial(name: string): string {
  const text = (name || 'AI').trim();
  return text.slice(0, 1).toUpperCase();
}

function mcpServerCount(agent: AgentItem): number {
  return Object.keys(agent.mcp_servers || {}).length;
}

function enabledMcpServerCount(agent: AgentItem): number {
  return Object.values(agent.mcp_servers || {}).filter((config) => config.enabled ?? true).length;
}

function agentOperationalState(agent: AgentItem, capabilityCount: number): { status: AgentBadgeStatus; label: string } {
  if (!agent.model) return { status: 'warning', label: '待配置' };
  if (capabilityCount === 0 && !agent.knowledge_enabled) return { status: 'default', label: '基础对话' };
  return { status: 'success', label: '可服务' };
}

function buildAgentMetadata(
  existing: Record<string, unknown> | undefined,
  values: Pick<AgentFormValues, 'avatar_key' | 'position' | 'role_intro'>,
): Record<string, unknown> {
  const metadata = { ...(existing || {}) };
  metadata.avatar_key = avatarOptionByKey(values.avatar_key).key;
  const position = (values.position || '').trim();
  if (position) {
    metadata.position = position;
  } else {
    delete metadata.position;
  }
  const roleIntro = (values.role_intro || '').trim();
  if (roleIntro) {
    metadata.role_intro = roleIntro;
  } else {
    delete metadata.role_intro;
  }
  return metadata;
}

interface AgentAvatarTriggerProps {
  value?: string;
  onChange?: (value: string) => void;
  name?: string;
  size?: 'normal' | 'large';
}

function AgentAvatarTrigger({ value, onChange, name = 'AI 员工', size = 'normal' }: AgentAvatarTriggerProps) {
  const [open, setOpen] = useState(false);
  const selectedAvatar = avatarOptionByKey(value);
  const avatarSize = size === 'large' ? 64 : 48;

  const content = (
    <div className="agent-avatar-popover">
      <Typography.Title level={5} className="agent-avatar-popover-title">
        选择 AI 员工形象
      </Typography.Title>
      <div className="agent-avatar-popover-grid">
        {AGENT_AVATAR_OPTIONS.map((option) => (
          <button
            key={option.key}
            type="button"
            className={`agent-avatar-option${option.key === selectedAvatar.key ? ' agent-avatar-option-selected' : ''}`}
            onClick={() => {
              onChange?.(option.key);
              setOpen(false);
            }}
            aria-label={option.label}
          >
            <img src={option.src} alt={option.label} draggable={false} />
          </button>
        ))}
      </div>
    </div>
  );

  return (
    <Popover
      content={content}
      trigger="click"
      open={open}
      onOpenChange={setOpen}
      placement="bottomLeft"
      arrow={{ pointAtCenter: true }}
      classNames={{ root: 'agent-avatar-popover-root' }}
    >
      <button type="button" className={`agent-avatar-trigger agent-avatar-trigger-${size}`} aria-label="选择员工头像">
        <Avatar size={avatarSize} src={selectedAvatar.src} className="agent-profile-avatar">
          {agentInitial(name)}
        </Avatar>
        <span className="agent-avatar-edit">
          <EditOutlined />
        </span>
      </button>
    </Popover>
  );
}

export default function AgentsPage() {
  const navigate = useNavigate();
  const { tenantId: currentTenantId, refreshAgentOptions, setAgentScope } = useRuntimeScope();
  const [loading, setLoading] = useState(false);
  const [tenants, setTenants] = useState<TenantItem[]>([]);
  const [tenantId, setTenantId] = useState(currentTenantId);
  const [agents, setAgents] = useState<AgentItem[]>([]);
  const [tools, setTools] = useState<ToolItem[]>([]);
  const [skills, setSkills] = useState<SkillItem[]>([]);
  const [availableModels, setAvailableModels] = useState<ModelConfigItem[]>([]);
  const [createOpen, setCreateOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [search, setSearch] = useState('');
  const [createForm] = Form.useForm<AgentFormValues>();

  const modelOptions = useMemo(() => {
    const options = availableModels.map((item) => ({
      label: item.display_name || item.model_name,
      value: item.model_config_id,
    }));
    const configuredIds = new Set(availableModels.map((item) => item.model_config_id));
    const legacyModels = agents
      .filter((agent) => agent.model && (!agent.model_config_id || !configuredIds.has(agent.model_config_id)))
      .map((agent) => agent.model);
    for (const model of Array.from(new Set(legacyModels))) {
      options.push({ label: `${model}（历史配置）`, value: `${LEGACY_MODEL_PREFIX}${model}` });
    }
    return options;
  }, [agents, availableModels]);

  const resolveModelSelection = (selection: string) => {
    if (selection.startsWith(LEGACY_MODEL_PREFIX)) {
      return { model: selection.slice(LEGACY_MODEL_PREFIX.length), model_config_id: '' };
    }
    const config = availableModels.find((item) => item.model_config_id === selection);
    return {
      model: config?.model_name || '',
      model_config_id: config?.model_config_id || '',
    };
  };



  const filteredAgents = useMemo(() => {
    const keyword = search.trim().toLowerCase();
    if (!keyword) return agents;
    return agents.filter((agent) => (
      displayAgentName(agent.agent_id, agent.name).toLowerCase().includes(keyword)
      || agent.agent_id.toLowerCase().includes(keyword)
      || agent.model.toLowerCase().includes(keyword)
    ));
  }, [agents, search]);

  const agentOverview = useMemo(() => {
    const capabilityTotal = agents.reduce((total, agent) => (
      total
      + effectiveToolNames(agent, tools).length
      + effectiveSkillNames(agent, skills).length
      + mcpServerCount(agent)
    ), 0);
    return {
      total: agents.length,
      serviceable: agents.filter((agent) => {
        const capabilityCount = effectiveToolNames(agent, tools).length
          + effectiveSkillNames(agent, skills).length
          + mcpServerCount(agent);
        return agentOperationalState(agent, capabilityCount).status === 'success';
      }).length,
      knowledgeEnabled: agents.filter((agent) => agent.knowledge_enabled).length,
      capabilityTotal,
    };
  }, [agents, skills, tools]);

  const loadTenants = async () => {
    const data = await api.listTenants();
    setTenants(data.tenants || []);
  };

  const loadAgents = async (tenant = tenantId) => {
    setLoading(true);
    try {
      const data = await api.listAgents(tenant);
      setAgents(data.agents || []);
    } finally {
      setLoading(false);
    }
  };

  const loadCapabilities = async (tenant = tenantId) => {
    const [toolData, skillData, modelData] = await Promise.all([
      api.listTools(),
      api.listSkills({ tenantId: tenant, agentId: '', bindingId: '' }),
      api.listAvailableModels(tenant),
    ]);
    setTools(toolData.tools || []);
    setSkills(skillData.skills || []);
    setAvailableModels(modelData.models || []);
  };

  const openCreate = () => {
    createForm.setFieldsValue({
      tenant_id: tenantId,
      agent_id: '',
      name: '',
      position: DEFAULT_AGENT_POSITION,
      role_intro: '',
      avatar_key: DEFAULT_AGENT_AVATAR_KEY,
      model_config_id: availableModels[0]?.model_config_id || '',
      system_prompt: '',
      tools: [],
      skills: [],
      knowledge_enabled: false,
    });
    setCreateOpen(true);
  };

  const openDetail = (row: AgentItem) => {
    navigate(`/agents/${row.agent_id}`);
  };

  const onCreateSubmit = async () => {
    const values = await createForm.validateFields();
    const effectiveTenantId = values.tenant_id || tenantId || currentTenantId;
    const modelSelection = resolveModelSelection(values.model_config_id || '');
    const payload = formatAgentPayload({
      tenant_id: effectiveTenantId,
      agent_id: values.agent_id || undefined,
      name: values.name,
      model: modelSelection.model,
      model_config_id: modelSelection.model_config_id,
      system_prompt: values.system_prompt,
      metadata: buildAgentMetadata(undefined, values),
      tools: values.tools || [],
      skills: values.skills || [],
      knowledge_enabled: values.knowledge_enabled,
      mcp_servers: {},
    });

    setSubmitting(true);
    try {
      await api.createAgent(payload);
      message.success('AI 员工已创建');
      setCreateOpen(false);
      await loadAgents(effectiveTenantId);
      await refreshAgentOptions();
    } finally {
      setSubmitting(false);
    }
  };

  const onDelete = async (row: AgentItem) => {
    await api.deleteAgent(row.tenant_id, row.agent_id);
    message.success('AI 员工已删除');

    await loadAgents(row.tenant_id);
    await refreshAgentOptions();
  };

  const startChatWithAgent = (agent: AgentItem) => {
    setAgentScope(agent.agent_id);
    navigate('/chat');
  };

  useEffect(() => {
    void loadTenants();
  }, []);

  useEffect(() => {
    setTenantId(currentTenantId);
  }, [currentTenantId]);

  useEffect(() => {
    void loadAgents(tenantId);
    void loadCapabilities(tenantId);
  }, [tenantId]);



  return (
    <ConsolePage
      className="agents-page"
      title="AI 员工"
      actions={(
        <PageToolbar>
          <Button icon={<ReloadOutlined />} onClick={() => void loadAgents(tenantId)}>刷新</Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>新员工入职</Button>
        </PageToolbar>
      )}
    >

      <MetricStrip
        className="agent-overview-metrics"
        items={[
          { key: 'total', title: '在岗员工', value: agentOverview.total, loading, tone: 'processing' },
          { key: 'serviceable', title: '可独立服务', value: agentOverview.serviceable, loading, tone: 'success' },
          { key: 'knowledge', title: '带知识库', value: agentOverview.knowledgeEnabled, loading },
          { key: 'capability', title: '能力连接', value: agentOverview.capabilityTotal, loading },
        ]}
      />

      <ConsoleFilterBar className="agent-filter-strip">
        <Select
          value={tenantId}
          className="agent-tenant-filter"
          aria-label="租户"
          onChange={(value) => setTenantId(value)}
          options={(tenants.length > 0 ? tenants : [{ tenant_id: 'default', name: 'default' }]).map((tenant) => ({
            label: tenant.name,
            value: tenant.tenant_id,
          }))}
        />
        <Input
          allowClear
          prefix={<SearchOutlined />}
          placeholder="搜索员工..."
          aria-label="搜索员工"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          className="agent-search"
        />
      </ConsoleFilterBar>

      {filteredAgents.length === 0 && !loading ? (
        <div className="agent-empty-card">
          <Empty description={search ? '没有匹配的 AI 员工。' : '暂无 AI 员工。'}>
            <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>新员工入职</Button>
          </Empty>
        </div>
      ) : (
        <div className="employee-grid">
          {filteredAgents.map(agent => {
            const agentName = displayAgentName(agent.agent_id, agent.name);
            const avatar = agentAvatarOption(agent);
            const position = String(agent.metadata?.position || DEFAULT_AGENT_POSITION);
            const toolCount = effectiveToolNames(agent, tools).length;
            const skillCount = effectiveSkillNames(agent, skills).length;
            const capabilityCount = toolCount + skillCount + mcpServerCount(agent);
            const state = agentOperationalState(agent, capabilityCount);
            const isDefault = isDefaultAgent(agent);

            return (
              <EmployeeCard
                key={agent.agent_id}
                name={agentName}
                id={agent.agent_id}
                position={position}
                avatarSrc={avatar.src}
                initial={agentInitial(agentName)}
                status={state.status}
                statusLabel={state.label}
                model={agent.model}
                tags={agent.knowledge_enabled ? [<Tag key="knowledge" color="green">知识库</Tag>] : []}
                metrics={[
                  { key: 'tools', label: '工具', value: toolCount, icon: <ToolOutlined />, tooltip: `挂载了 ${toolCount} 个工具` },
                  { key: 'skills', label: '技能', value: skillCount, icon: <BuildOutlined />, tooltip: `挂载了 ${skillCount} 个技能` },
                  { key: 'mcp', label: 'MCP', value: enabledMcpServerCount(agent), icon: <ApiOutlined />, tooltip: `启用了 ${enabledMcpServerCount(agent)} 个 MCP` },
                ]}
                actions={[
                  { key: 'config', label: '配置', icon: <SettingOutlined />, onClick: () => openDetail(agent) },
                  { key: 'chat', label: '对话', icon: <MessageOutlined />, onClick: () => startChatWithAgent(agent) },
                  {
                    key: 'delete',
                    label: '删除',
                    icon: <DeleteOutlined />,
                    danger: true,
                    disabled: isDefault,
                    tooltip: isDefault ? '通用 AI 员工不能删除' : '删除',
                    confirmTitle: isDefault ? undefined : '确认删除该 AI 员工？',
                    onClick: () => void onDelete(agent),
                  },
                ]}
              />
            );
          })}
        </div>
      )}

      <Modal
        open={createOpen}
        title="新员工入职"
        onCancel={() => setCreateOpen(false)}
        onOk={() => void onCreateSubmit()}
        confirmLoading={submitting}
        width="min(51.25rem, calc(100vw - 3rem))"
        destroyOnClose
      >
        <Form form={createForm} layout="vertical">
          <div className="agent-create-profile">
            <Form.Item name="avatar_key" rules={[{ required: true, message: '请选择员工头像' }]} noStyle>
              <AgentAvatarTrigger name="新员工" size="large" />
            </Form.Item>
            <div className="agent-create-profile-copy">
              <Typography.Title level={4}>新员工</Typography.Title>
              <Typography.Text type="secondary">设置该 AI 员工的基础资料、角色简介与响应模型</Typography.Text>
            </div>
          </div>
          <Form.Item name="tenant_id" label="租户" hidden={tenants.length <= 1}>
            <Select
              aria-label="租户"
              options={(tenants.length > 0 ? tenants : [{ tenant_id: 'default', name: 'default' }]).map((tenant) => ({
                label: tenant.name,
                value: tenant.tenant_id,
              }))}
            />
          </Form.Item>
          <div className="agent-create-grid">
            <Form.Item name="agent_id" label="员工 ID">
              <Input placeholder="留空则自动生成" aria-label="员工 ID" />
            </Form.Item>
            <Form.Item name="name" label="员工昵称" rules={[{ required: true, message: '请输入员工昵称' }]}>
              <Input placeholder="例如：支付通客服" aria-label="员工昵称" />
            </Form.Item>
            <Form.Item name="position" label="职位">
              <Input placeholder="例如：AI 业务专员" aria-label="职位" />
            </Form.Item>
            <Form.Item name="model_config_id" label="模型" rules={[{ required: true, message: '请选择模型' }]}>
              <Select
                showSearch
                allowClear
                aria-label="模型"
                options={modelOptions}
                placeholder="选择平台或租户模型"
              />
            </Form.Item>
          </div>
          <Form.Item name="role_intro" label="角色简介">
            <Input.TextArea rows={3} placeholder="用一两句话描述该 AI 员工的角色、擅长领域和服务边界。" aria-label="角色简介" />
          </Form.Item>
          <Form.Item name="system_prompt" label="核心指令" htmlFor="agent-create-system-prompt">
            <Input.TextArea id="agent-create-system-prompt" rows={5} placeholder="设置该 AI 员工的身份、边界、语气和工作流程。" aria-label="核心指令" />
          </Form.Item>
          <Form.Item name="tools" label="工具">
            <Select
              mode="multiple"
              allowClear
              aria-label="工具"
              options={tools.map((tool) => ({
                label: tool.description ? `${tool.name} - ${tool.description}` : tool.name,
                value: tool.name,
              }))}
              placeholder="选择工具"
            />
          </Form.Item>
          <Form.Item name="skills" label="技能">
            <Select
              mode="multiple"
              allowClear
              aria-label="技能"
              options={skills.map((skill) => ({
                label: skill.description ? `${skill.name} - ${skill.description}` : skill.name,
                value: skill.name,
              }))}
              placeholder="选择技能"
            />
          </Form.Item>
          <Form.Item name="knowledge_enabled" label="启用知识库" htmlFor="agent-create-knowledge-enabled" valuePropName="checked"><Switch id="agent-create-knowledge-enabled" aria-label="启用知识库" /></Form.Item>
        </Form>
      </Modal>
    </ConsolePage>
  );
}
