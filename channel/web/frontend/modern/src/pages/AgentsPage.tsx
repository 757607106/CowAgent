import {
  ApiOutlined,
  AppstoreOutlined,
  ArrowLeftOutlined,
  BookOutlined,
  BranchesOutlined,
  BuildOutlined,
  DatabaseOutlined,
  MessageOutlined,
  PlusOutlined,
  ReloadOutlined,
  SaveOutlined,
  SearchOutlined,
  SettingOutlined,
  ToolOutlined,
} from '@ant-design/icons';
import {
  Avatar,
  Badge,
  Button,
  Card,
  Checkbox,
  Empty,
  Form,
  Input,
  Modal,
  Popconfirm,
  Segmented,
  Select,
  Space,
  Statistic,
  Switch,
  Tabs,
  Tag,
  Typography,
  message,
} from 'antd';
import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ConsolePage, DataTableShell, PageToolbar, StatusTag } from '../components/console';
import { displayAgentName, useRuntimeScope } from '../context/runtime';
import { api, formatAgentPayload } from '../services/api';
import type { AgentItem, ModelConfigItem, RuntimeScope, SkillItem, TenantItem, ToolItem } from '../types';
import { KnowledgePanel } from './KnowledgePage';
import { MemoryPanel } from './MemoryPage';

interface AgentFormValues {
  tenant_id: string;
  agent_id: string;
  name: string;
  model_config_id: string;
  system_prompt: string;
  tools: string[];
  skills: string[];
  knowledge_enabled: boolean;
}

type AgentViewMode = 'table' | 'cards';
type AgentBadgeStatus = 'success' | 'processing' | 'default' | 'warning' | 'error';
type McpServerMap = NonNullable<AgentItem['mcp_servers']>;

const LEGACY_MODEL_PREFIX = 'legacy-model:';

function selectedCountText(count: number): string {
  return count > 0 ? `${count} 已选择` : '未选择';
}

function toggleListItem(list: string[], name: string, checked: boolean): string[] {
  if (checked) return Array.from(new Set([...list, name]));
  return list.filter((item) => item !== name);
}

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

function sameNameSet(left: string[], right: string[]): boolean {
  if (left.length !== right.length) return false;
  const selected = new Set(left);
  return right.every((name) => selected.has(name));
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

function agentWorkline(agent: AgentItem, toolCount: number, skillCount: number, mcpCount: number): string {
  if (!agent.model) return '还缺少模型配置，补齐后才能稳定接入业务。';
  if (mcpCount > 0) return '已接入外部服务，可把对话延展到真实工作流。';
  if (skillCount > 0) return '带有可复用技能，适合持续处理一类业务任务。';
  if (toolCount > 0) return '拥有工具权限，可在会话中执行具体动作。';
  if (agent.knowledge_enabled) return '已接入知识库，适合回答团队内部资料问题。';
  return '保持轻量待命，适合做基础问答和角色化沟通。';
}

function applyMcpEnabledState(
  agentServers: McpServerMap,
  enabledMap: Record<string, boolean>,
  catalogServers: McpServerMap,
): McpServerMap {
  const names = Array.from(new Set([
    ...Object.keys(catalogServers),
    ...Object.keys(agentServers),
  ]));
  const next: McpServerMap = {};

  names.forEach((name) => {
    const catalogConfig = catalogServers[name];
    const agentConfig = agentServers[name];
    const checked = enabledMap[name];

    if (checked) {
      if (catalogConfig) {
        next[name] = { enabled: true };
        return;
      }
      if (agentConfig) {
        next[name] = {
          ...agentConfig,
          enabled: true,
        };
      }
    }
  });

  return next;
}

function collectBindableMcpServers(catalogServers: McpServerMap, agentServers: McpServerMap): McpServerMap {
  return {
    ...agentServers,
    ...catalogServers,
  };
}

function buildMcpBindingMap(agent: AgentItem, catalogServers: McpServerMap): Record<string, boolean> {
  const agentServers = agent.mcp_servers || {};
  const bindableServers = collectBindableMcpServers(catalogServers, agentServers);
  return Object.fromEntries(
    Object.keys(bindableServers).map((name) => [
      name,
      Boolean(agentServers[name] && (agentServers[name].enabled ?? true)),
    ]),
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
  const [detailSaving, setDetailSaving] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);
  const [selectedAgent, setSelectedAgent] = useState<AgentItem | null>(null);
  const [detailTab, setDetailTab] = useState('core');
  const [memoryTab, setMemoryTab] = useState('memory');
  const [search, setSearch] = useState('');
  const [agentView, setAgentView] = useState<AgentViewMode>('cards');
  const [selectedTools, setSelectedTools] = useState<string[]>([]);
  const [selectedSkills, setSelectedSkills] = useState<string[]>([]);
  const [mcpEnabledMap, setMcpEnabledMap] = useState<Record<string, boolean>>({});
  const [tenantMcpServers, setTenantMcpServers] = useState<McpServerMap>({});
  const [createForm] = Form.useForm<AgentFormValues>();
  const [detailForm] = Form.useForm<AgentFormValues>();

  const modelOptions = useMemo(() => {
    const options = availableModels.map((item) => ({
      label: `${item.display_name || item.model_name} (${item.provider})`,
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

  const tenantNameById = useMemo(
    () => new Map(tenants.map((tenant) => [tenant.tenant_id, tenant.name])),
    [tenants],
  );

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

  const selectedScope = useMemo<RuntimeScope | null>(() => {
    if (!selectedAgent) return null;
    return {
      tenantId: selectedAgent.tenant_id,
      agentId: selectedAgent.agent_id,
      bindingId: '',
    };
  }, [selectedAgent]);

  const bindableMcpServers = useMemo(
    () => collectBindableMcpServers(tenantMcpServers, selectedAgent?.mcp_servers || {}),
    [tenantMcpServers, selectedAgent],
  );

  const boundMcpCount = useMemo(
    () => Object.values(mcpEnabledMap).filter(Boolean).length,
    [mcpEnabledMap],
  );

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

  const loadTenantMcpServers = async (tenant = tenantId): Promise<McpServerMap> => {
    try {
      const data = await api.listMcpServers(tenant);
      const nextServers = Object.fromEntries(
        (data.servers || []).map((server) => [server.name, server]),
      ) as McpServerMap;
      setTenantMcpServers(nextServers);
      return nextServers;
    } catch {
      setTenantMcpServers({});
      return {};
    }
  };

  const loadCapabilities = async (tenant = tenantId, agentId = '') => {
    const [toolData, skillData, modelData, nextMcpServers] = await Promise.all([
      api.listTools(),
      api.listSkills({ tenantId: tenant, agentId, bindingId: '' }),
      api.listAvailableModels(tenant),
      loadTenantMcpServers(tenant),
    ]);
    const nextTools = toolData.tools || [];
    const nextSkills = skillData.skills || [];
    setTools(nextTools);
    setSkills(nextSkills);
    setAvailableModels(modelData.models || []);
    return { tools: nextTools, skills: nextSkills, mcpServers: nextMcpServers };
  };

  const fillDetailForm = (
    agent: AgentItem,
    availableTools = tools,
    availableSkills = skills,
    availableMcpServers = tenantMcpServers,
  ) => {
    const nextTools = effectiveToolNames(agent, availableTools);
    const nextSkills = effectiveSkillNames(agent, availableSkills);
    detailForm.setFieldsValue({
      tenant_id: agent.tenant_id,
      agent_id: agent.agent_id,
      name: displayAgentName(agent.agent_id, agent.name),
      model_config_id: agent.model_config_id || (agent.model ? `${LEGACY_MODEL_PREFIX}${agent.model}` : ''),
      system_prompt: agent.system_prompt || '',
      tools: nextTools,
      skills: nextSkills,
      knowledge_enabled: Boolean(agent.knowledge_enabled),
    });
    setSelectedTools(nextTools);
    setSelectedSkills(nextSkills);
    setMcpEnabledMap(buildMcpBindingMap(agent, availableMcpServers));
  };

  const openCreate = () => {
    createForm.setFieldsValue({
      tenant_id: tenantId,
      agent_id: '',
      name: '',
      model_config_id: availableModels[0]?.model_config_id || '',
      system_prompt: '',
      tools: [],
      skills: [],
      knowledge_enabled: false,
    });
    setCreateOpen(true);
  };

  const openDetail = async (row: AgentItem) => {
    setDetailLoading(true);
    try {
      const data = await api.getAgentDetail(row.tenant_id, row.agent_id);
      const agent = data.agent || row;
      setSelectedAgent(agent);
      setDetailTab('core');
      setMemoryTab('memory');
      const capabilityData = await loadCapabilities(agent.tenant_id, agent.agent_id);
      fillDetailForm(agent, capabilityData.tools, capabilityData.skills, capabilityData.mcpServers);
    } finally {
      setDetailLoading(false);
    }
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
      tools: values.tools || [],
      skills: values.skills || [],
      knowledge_enabled: values.knowledge_enabled,
      mcp_servers: {},
    });

    setSubmitting(true);
    try {
      await api.createAgent(payload);
      message.success('数字员工已创建');
      setCreateOpen(false);
      await loadAgents(effectiveTenantId);
      await refreshAgentOptions();
    } finally {
      setSubmitting(false);
    }
  };

  const saveDetail = async () => {
    if (!selectedAgent) return;
    const values = await detailForm.validateFields();
    const allToolNames = tools.map((tool) => tool.name);
    const allSkillNames = skills.map((skill) => skill.name);
    const nextTools = inheritsDefaultTools(selectedAgent) && sameNameSet(selectedTools, allToolNames)
      ? []
      : selectedTools;
    const nextSkills = inheritsDefaultSkills(selectedAgent) && sameNameSet(selectedSkills, allSkillNames)
      ? []
      : selectedSkills;
    const modelSelection = resolveModelSelection(values.model_config_id || '');
    const payload = formatAgentPayload({
      tenant_id: selectedAgent.tenant_id,
      agent_id: selectedAgent.agent_id,
      name: values.name,
      model: modelSelection.model,
      model_config_id: modelSelection.model_config_id,
      system_prompt: values.system_prompt,
      tools: nextTools,
      skills: nextSkills,
      knowledge_enabled: values.knowledge_enabled,
      mcp_servers: applyMcpEnabledState(
        selectedAgent.mcp_servers || {},
        mcpEnabledMap,
        tenantMcpServers,
      ),
    });

    setDetailSaving(true);
    try {
      const data = await api.updateAgent(selectedAgent.agent_id, payload);
      const updated = (data as { agent?: AgentItem }).agent || { ...selectedAgent, ...payload } as AgentItem;
      setSelectedAgent(updated);
      fillDetailForm(updated, tools, skills, tenantMcpServers);
      message.success('数字员工已保存');
      await loadAgents(selectedAgent.tenant_id);
      await refreshAgentOptions();
    } finally {
      setDetailSaving(false);
    }
  };

  const onDelete = async (row: AgentItem) => {
    await api.deleteAgent(row.tenant_id, row.agent_id);
    message.success('数字员工已删除');
    if (selectedAgent?.agent_id === row.agent_id && selectedAgent.tenant_id === row.tenant_id) {
      setSelectedAgent(null);
    }
    await loadAgents(row.tenant_id);
    await refreshAgentOptions();
  };

  const startChat = () => {
    if (!selectedAgent) return;
    setAgentScope(selectedAgent.agent_id);
    navigate('/chat');
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
    setSelectedAgent(null);
  }, [currentTenantId]);

  useEffect(() => {
    void loadAgents(tenantId);
    void loadCapabilities(tenantId);
  }, [tenantId]);

  if (selectedAgent) {
    const selectedAgentName = displayAgentName(selectedAgent.agent_id, selectedAgent.name);
    const selectedToolCount = effectiveToolNames(selectedAgent, tools).length;
    const selectedSkillCount = effectiveSkillNames(selectedAgent, skills).length;

    return (
      <div className="agent-detail-page">
        <Card className="agent-detail-hero" loading={detailLoading}>
          <div className="agent-detail-hero-main">
            <Avatar size={64} className="agent-avatar-large">
              {agentInitial(selectedAgentName)}
            </Avatar>
            <div className="agent-detail-title">
              <Space align="center" size={10} wrap>
                <Typography.Title level={3} className="agent-detail-heading">
                  {selectedAgentName}
                </Typography.Title>
                <StatusTag status="active">工作中</StatusTag>
              </Space>
              <Typography.Text type="secondary">
                {tenantNameById.get(selectedAgent.tenant_id) || selectedAgent.tenant_id} / {selectedAgent.agent_id}
              </Typography.Text>
            </div>
          </div>
          <Space wrap>
            <Button icon={<ArrowLeftOutlined />} onClick={() => setSelectedAgent(null)}>
              返回大厅
            </Button>
            <Button icon={<MessageOutlined />} onClick={startChat}>
              发起会话
            </Button>
            <Button type="primary" icon={<SaveOutlined />} loading={detailSaving} onClick={() => void saveDetail()}>
              保存变更
            </Button>
          </Space>
        </Card>

        <Tabs
          activeKey={detailTab}
          onChange={setDetailTab}
          items={[
            {
              key: 'core',
              label: '核心配置',
              icon: <SettingOutlined />,
              children: (
                <Card className="agent-section-card">
                  <Form form={detailForm} layout="vertical">
                    <div className="agent-core-grid">
                      <Form.Item name="name" label="员工名称" rules={[{ required: true, message: '请输入员工名称' }]}>
                        <Input placeholder="例如：支付通客服" aria-label="员工名称" />
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
                    <Form.Item name="system_prompt" label="角色设定与行为准则" htmlFor="agent-detail-system-prompt"><Input.TextArea id="agent-detail-system-prompt" rows={8} placeholder="设置该数字员工的身份、边界、语气和工作流程。" aria-label="角色设定与行为准则" /></Form.Item>
                    <div className="agent-knowledge-switch">
                      <div>
                        <Typography.Text strong>启用知识库</Typography.Text>
                        <div className="channel-field-hint">开启后，该员工会读取自己工作区内的知识库内容。</div>
                      </div>
                      <Form.Item name="knowledge_enabled" label="启用知识库" htmlFor="agent-detail-knowledge-enabled" valuePropName="checked" colon={false} className="agent-knowledge-switch-control"><Switch id="agent-detail-knowledge-enabled" aria-label="启用知识库" /></Form.Item>
                    </div>
                  </Form>
                  <div className="agent-section-actions">
                    <Button type="primary" icon={<SaveOutlined />} loading={detailSaving} onClick={() => void saveDetail()}>
                      保存核心配置
                    </Button>
                  </div>
                </Card>
              ),
            },
            {
              key: 'capabilities',
              label: `外接能力 (${selectedToolCount + selectedSkillCount})`,
              icon: <BranchesOutlined />,
              children: (
                <div className="agent-capability-stack">
                  <Card
                    className="agent-section-card"
                    title={<Space><ToolOutlined />工具</Space>}
                    extra={<Tag color={selectedTools.length ? 'blue' : 'default'}>{inheritsDefaultTools(selectedAgent) ? `全部 ${selectedTools.length}` : selectedCountText(selectedTools.length)}</Tag>}
                  >
                    {tools.length === 0 ? (
                      <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="当前没有可选择的工具。" />
                    ) : (
                      <div className="agent-capability-grid">
                        {tools.map((tool) => (
                          <label key={tool.name} className="agent-capability-item">
                            <span>
                              <Typography.Text strong>{tool.name}</Typography.Text>
                              <Typography.Paragraph type="secondary" ellipsis={{ rows: 2 }} className="compact-paragraph">
                                {tool.description || '该工具未提供描述。'}
                              </Typography.Paragraph>
                            </span>
                            <Checkbox
                              checked={selectedTools.includes(tool.name)}
                              onChange={(event) => setSelectedTools((prev) => toggleListItem(prev, tool.name, event.target.checked))}
                            />
                          </label>
                        ))}
                      </div>
                    )}
                  </Card>

                  <Card
                    className="agent-section-card"
                    title={<Space><BuildOutlined />技能</Space>}
                    extra={<Tag color={selectedSkills.length ? 'geekblue' : 'default'}>{inheritsDefaultSkills(selectedAgent) ? `全部 ${selectedSkills.length}` : selectedCountText(selectedSkills.length)}</Tag>}
                  >
                    {skills.length === 0 ? (
                      <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="当前员工空间还没有可选择的技能。" />
                    ) : (
                      <div className="agent-capability-grid">
                        {skills.map((skill) => (
                          <label key={skill.name} className="agent-capability-item">
                            <span>
                              <Typography.Text strong>{skill.name}</Typography.Text>
                              <Typography.Paragraph type="secondary" ellipsis={{ rows: 2 }} className="compact-paragraph">
                                {skill.description || '该技能未提供描述。'}
                              </Typography.Paragraph>
                            </span>
                            <Checkbox
                              checked={selectedSkills.includes(skill.name)}
                              onChange={(event) => setSelectedSkills((prev) => toggleListItem(prev, skill.name, event.target.checked))}
                            />
                          </label>
                        ))}
                      </div>
                    )}
                  </Card>

                  <Card
                    className="agent-section-card"
                    title={<Space><ApiOutlined />MCP 连接</Space>}
                    extra={<Tag color={boundMcpCount ? 'cyan' : 'default'}>{boundMcpCount} 已绑定 / {Object.keys(bindableMcpServers).length} 可用</Tag>}
                  >
                    {Object.keys(bindableMcpServers).length === 0 ? (
                      <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="当前租户还没有可绑定的 MCP Server，请先在 MCP 服务管理页新增。" />
                    ) : (
                      <div className="agent-mcp-grid">
                        {Object.entries(bindableMcpServers).map(([name, config]) => {
                          const bound = Boolean(mcpEnabledMap[name]);
                          return (
                            <label key={name} className="agent-mcp-item">
                              <span>
                                <Space size={8} wrap>
                                  <Typography.Text strong>{name}</Typography.Text>
                                  <Tag color={bound ? 'green' : 'default'}>
                                    {bound ? '已绑定' : '未绑定'}
                                  </Tag>
                                </Space>
                                <Typography.Paragraph type="secondary" ellipsis={{ rows: 2 }} className="compact-paragraph">
                                  {config.command ? 'MCP 服务配置已就绪' : '未配置启动命令'} {(config.args || []).length ? ` / 参数 ${config.args?.length}` : ''}
                                </Typography.Paragraph>
                              </span>
                              <Checkbox
                                checked={bound}
                                onChange={(event) => setMcpEnabledMap((prev) => ({
                                  ...prev,
                                  [name]: event.target.checked,
                                }))}
                              />
                            </label>
                          );
                        })}
                      </div>
                    )}
                  </Card>

                  <div className="agent-section-actions">
                    <Button type="primary" icon={<SaveOutlined />} loading={detailSaving} onClick={() => void saveDetail()}>
                      保存外接能力
                    </Button>
                  </div>
                </div>
              ),
            },
            {
              key: 'memory',
              label: '长期记忆',
              icon: <DatabaseOutlined />,
              children: selectedScope ? (
                <div className="agent-memory-shell">
                  <Typography.Text type="secondary">
                    当前仅查看 {selectedAgentName} 的独立记忆空间，其他数字员工的记忆不会出现在这里。
                  </Typography.Text>
                  <Tabs
                    activeKey={memoryTab}
                    onChange={setMemoryTab}
                    items={[
                      {
                        key: 'memory',
                        label: '记忆与梦境',
                        icon: <DatabaseOutlined />,
                        children: (
                          <MemoryPanel
                            scope={selectedScope}
                            title="员工记忆"
                            description="查看该数字员工自己的记忆文件与梦境日记。"
                            embedded
                          />
                        ),
                      },
                      {
                        key: 'knowledge',
                        label: '知识库',
                        icon: <BookOutlined />,
                        children: (
                          <KnowledgePanel
                            scope={selectedScope}
                            title="员工知识库"
                            description="浏览该数字员工自己的知识库文档和知识图谱。"
                            embedded
                          />
                        ),
                      },
                    ]}
                  />
                </div>
              ) : null,
            },
          ]}
        />
      </div>
    );
  }

  const agentColumns = [
    {
      title: '员工',
      key: 'agent',
      width: 260,
      render: (_: unknown, agent: AgentItem) => {
        const agentName = displayAgentName(agent.agent_id, agent.name);
        const toolCount = effectiveToolNames(agent, tools).length;
        const skillCount = effectiveSkillNames(agent, skills).length;
        const capabilityCount = toolCount + skillCount + mcpServerCount(agent);
        const state = agentOperationalState(agent, capabilityCount);
        return (
          <div className="agent-table-name">
            <Avatar size={40} className="agent-avatar">{agentInitial(agentName)}</Avatar>
            <div className="agent-table-title">
              <Space size={8} wrap>
                <Typography.Text strong>{agentName}</Typography.Text>
                <Badge status={state.status} text={state.label} />
              </Space>
              <Typography.Text type="secondary">{agent.agent_id}</Typography.Text>
            </div>
          </div>
        );
      },
    },
    {
      title: '模型',
      dataIndex: 'model',
      width: 180,
      render: (value: string) => value ? <Tag color="blue">{value}</Tag> : <Tag>未配置</Tag>,
    },
    {
      title: '能力',
      key: 'capabilities',
      width: 260,
      render: (_: unknown, agent: AgentItem) => {
        const toolCount = effectiveToolNames(agent, tools).length;
        const skillCount = effectiveSkillNames(agent, skills).length;
        const enabledMcpCount = enabledMcpServerCount(agent);
        return (
          <div className="agent-table-ability">
            <Tag icon={<ToolOutlined />}>工具 {toolCount}</Tag>
            <Tag icon={<BuildOutlined />}>技能 {skillCount}</Tag>
            <Tag icon={<ApiOutlined />}>MCP {enabledMcpCount}</Tag>
          </div>
        );
      },
    },
    {
      title: '知识库',
      dataIndex: 'knowledge_enabled',
      width: 120,
      render: (enabled: boolean) => enabled ? <Tag color="green">已启用</Tag> : <Tag>未启用</Tag>,
    },
    {
      title: '租户',
      dataIndex: 'tenant_id',
      width: 180,
      ellipsis: true,
      render: (value: string) => tenantNameById.get(value) || value,
    },
    {
      title: '操作',
      key: 'actions',
      width: 170,
      fixed: 'right' as const,
      render: (_: unknown, agent: AgentItem) => (
        <Space size={4}>
          <Button type="link" icon={<AppstoreOutlined />} onClick={() => void openDetail(agent)}>
            配置
          </Button>
          <Popconfirm
            title={isDefaultAgent(agent) ? '通用 Agent 不能删除' : '确认删除该数字员工？'}
            onConfirm={() => void onDelete(agent)}
            disabled={isDefaultAgent(agent)}
          >
            <Button type="link" danger disabled={isDefaultAgent(agent)}>删除</Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <ConsolePage
      className="agents-page"
      title="AI 员工"
      actions={(
          <PageToolbar>
            <Segmented
              value={agentView}
              onChange={(value) => setAgentView(value as AgentViewMode)}
              options={[
                { label: '员工视图', value: 'cards' },
                { label: '运营表格', value: 'table' },
              ]}
            />
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
            <Button icon={<ReloadOutlined />} onClick={() => void loadAgents(tenantId)}>刷新</Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>新员工入职</Button>
          </PageToolbar>
        )}
    >

      {agentView === 'table' ? (
        <div className="agent-overview-grid">
          <Card className="agent-overview-card">
            <Statistic title="在岗员工" value={agentOverview.total} loading={loading} />
          </Card>
          <Card className="agent-overview-card">
            <Statistic title="可独立服务" value={agentOverview.serviceable} loading={loading} />
          </Card>
          <Card className="agent-overview-card">
            <Statistic title="带知识库" value={agentOverview.knowledgeEnabled} loading={loading} />
          </Card>
          <Card className="agent-overview-card">
            <Statistic title="能力连接" value={agentOverview.capabilityTotal} loading={loading} />
          </Card>
        </div>
      ) : null}

      {filteredAgents.length === 0 && !loading ? (
        <Card className="agent-empty-card">
          <Empty description={search ? '没有匹配的数字员工。' : '暂无数字员工。'}>
            <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>新员工入职</Button>
          </Empty>
        </Card>
      ) : agentView === 'table' ? (
        <DataTableShell<AgentItem>
            title="员工列表"
            rowKey={(agent) => `${agent.tenant_id}/${agent.agent_id}`}
            loading={loading}
            columns={agentColumns}
            dataSource={filteredAgents}
            pagination={{ pageSize: 8, showSizeChanger: false }}
            scroll={{ x: 1080 }}
          />
      ) : (
        <div className="agent-card-grid">
          {filteredAgents.map((agent) => {
            const agentName = displayAgentName(agent.agent_id, agent.name);
            const toolCount = effectiveToolNames(agent, tools).length;
            const skillCount = effectiveSkillNames(agent, skills).length;
            const mcpCount = mcpServerCount(agent);
            const state = agentOperationalState(agent, toolCount + skillCount + mcpCount);
            const capabilityCount = toolCount + skillCount + mcpCount + (agent.knowledge_enabled ? 1 : 0);
            const tags = [
              '官方认证',
              agent.knowledge_enabled ? '知识库' : '通用行业',
              skillCount > 0 ? 'AI助手' : '基础对话',
              mcpCount > 0 ? '外部服务' : agent.model || '待配置',
            ];
            return (
              <Card
                key={`${agent.tenant_id}/${agent.agent_id}`}
                hoverable
                className="agent-card agent-resource-card"
                loading={loading}
              >
                <div className="agent-market-body">
                  <div className="agent-resource-head">
                    <Avatar size={44} className="agent-market-avatar">{agentInitial(agentName)}</Avatar>
                    <span className={`agent-status-pulse agent-status-${state.status}`} />
                  </div>
                  <Space size={8} wrap>
                    <Typography.Title level={5} className="agent-card-heading">
                      {agentName}
                    </Typography.Title>
                    <Badge status={state.status} text={state.label} />
                  </Space>
                  <div className="agent-market-tags">
                    {tags.map((tag) => <Tag key={tag}>{tag}</Tag>)}
                  </div>
                </div>
                <Typography.Paragraph className="agent-market-desc" type="secondary" ellipsis={{ rows: 2 }}>
                  {agent.system_prompt || '负责特定业务场景的数字员工，可独立完成连续任务。'}
                </Typography.Paragraph>
                <div className="agent-market-footer">
                  <Typography.Text type="secondary">
                    <BranchesOutlined /> 能力 {capabilityCount}
                  </Typography.Text>
                  <Space size={8}>
                    <Button type="text" icon={<SettingOutlined />} onClick={() => void openDetail(agent)}>
                      配置
                    </Button>
                    <Button type="primary" icon={<AppstoreOutlined />} onClick={() => startChatWithAgent(agent)}>
                      应用
                    </Button>
                  </Space>
                </div>
                <Typography.Text className="agent-market-workline" type="secondary">
                  {agentWorkline(agent, toolCount, skillCount, mcpCount)}
                </Typography.Text>
              </Card>
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
        width={760}
        destroyOnClose
      >
        <Form form={createForm} layout="vertical">
          <Form.Item name="tenant_id" label="租户" hidden={tenants.length <= 1}>
            <Select
              aria-label="租户"
              options={(tenants.length > 0 ? tenants : [{ tenant_id: 'default', name: 'default' }]).map((tenant) => ({
                label: tenant.name,
                value: tenant.tenant_id,
              }))}
            />
          </Form.Item>
          <Form.Item name="agent_id" label="员工 ID">
            <Input placeholder="留空则自动生成" aria-label="员工 ID" />
          </Form.Item>
          <Form.Item name="name" label="员工名称" rules={[{ required: true, message: '请输入员工名称' }]}>
            <Input placeholder="例如：支付通客服" aria-label="员工名称" />
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
          <Form.Item name="system_prompt" label="角色设定与行为准则" htmlFor="agent-create-system-prompt">
            <Input.TextArea id="agent-create-system-prompt" rows={5} aria-label="角色设定与行为准则" />
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
