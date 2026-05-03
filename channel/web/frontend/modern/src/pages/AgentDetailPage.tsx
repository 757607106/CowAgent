import {
  ApiOutlined,
  ArrowLeftOutlined,
  BookOutlined,
  BranchesOutlined,
  BuildOutlined,
  DatabaseOutlined,
  MessageOutlined,
  SaveOutlined,
  SettingOutlined,
  ToolOutlined,
} from '@ant-design/icons';
import {
  Breadcrumb,
  Button,
  Card,
  Empty,
  Form,
  Input,
  Select,
  Space,
  Spin,
  Switch,
  Tabs,
  Typography,
  message,
} from 'antd';
import { useEffect, useMemo, useState } from 'react';
import { useNavigate, useParams, Link } from 'react-router-dom';
import { ConsolePage, StatusTag } from '../components/console';
import { displayAgentName, useRuntimeScope } from '../context/runtime';
import { api, formatAgentPayload } from '../services/api';
import type { AgentItem, McpServerItem, ModelConfigItem, RuntimeScope, SkillItem, ToolItem } from '../types';
import { KnowledgePanel } from './KnowledgePage';
import { MemoryPanel } from './MemoryPage';

const DEFAULT_AGENT_POSITION = 'AI 业务专员';

function toggleListItem(list: string[], name: string, checked: boolean): string[] {
  if (checked) return Array.from(new Set([...list, name]));
  return list.filter((item) => item !== name);
}

function isDefaultAgent(agent: AgentItem | null | undefined): boolean {
  return agent?.agent_id === 'default';
}

function effectiveToolNames(agent: AgentItem, availableTools: ToolItem[]): string[] {
  if (isDefaultAgent(agent) && !(agent?.tools || []).length) return availableTools.map((t) => t.name);
  return agent.tools || [];
}

function effectiveSkillNames(agent: AgentItem, availableSkills: SkillItem[]): string[] {
  if (isDefaultAgent(agent) && !(agent?.skills || []).length) return availableSkills.map((s) => s.name);
  return agent.skills || [];
}

export default function AgentDetailPage() {
  const { tenantId, setAgentScope } = useRuntimeScope();
  const { agentId } = useParams<{ agentId: string }>();
  const navigate = useNavigate();

  const [form] = Form.useForm();
  const [agent, setAgent] = useState<AgentItem | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [activeTab, setActiveTab] = useState('core');

  const [availableModels, setAvailableModels] = useState<ModelConfigItem[]>([]);
  const [tools, setTools] = useState<ToolItem[]>([]);
  const [skills, setSkills] = useState<SkillItem[]>([]);
  const [tenantMcpServers, setTenantMcpServers] = useState<McpServerItem[]>([]);

  const [selectedTools, setSelectedTools] = useState<string[]>([]);
  const [selectedSkills, setSelectedSkills] = useState<string[]>([]);
  const [mcpEnabledMap, setMcpEnabledMap] = useState<Record<string, boolean>>({});

  const modelOptions = useMemo(() => {
    if (!availableModels.length) return [];
    return availableModels.map((item) => ({
      label: item.display_name || item.model_name,
      value: item.model_config_id,
    }));
  }, [availableModels]);

  const scope = useMemo<RuntimeScope | null>(() => {
    if (!agent) return null;
    return { tenantId: agent.tenant_id, agentId: agent.agent_id, bindingId: '' };
  }, [agent]);

  const loadData = async () => {
    if (!agentId || !tenantId) return;
    setLoading(true);
    try {
      const runtimeScope: RuntimeScope = { tenantId, agentId, bindingId: '' };
      const [agentData, toolData, skillData, modelData, mcpData] = await Promise.all([
        api.getAgentDetail(tenantId, agentId),
        api.listTools(),
        api.listSkills(runtimeScope),
        api.listAvailableModels(tenantId),
        api.listMcpServers(tenantId),
      ]);

      const loadedAgent = agentData.agent;
      if (!loadedAgent) throw new Error('Agent not found');
      setAgent(loadedAgent);

      const loadedTools = toolData.tools || [];
      const loadedSkills = skillData.skills || [];
      setTools(loadedTools);
      setSkills(loadedSkills);
      setAvailableModels(modelData.models || []);
      setTenantMcpServers(mcpData.servers || []);

      // Initialize form
      const agentMeta = loadedAgent.metadata || {};
      form.setFieldsValue({
        name: loadedAgent.name || loadedAgent.agent_id,
        position: agentMeta.position || DEFAULT_AGENT_POSITION,
        role_intro: agentMeta.role_intro || '',
        model_config_id: loadedAgent.model_config_id || '',
        system_prompt: loadedAgent.system_prompt || '',
        knowledge_enabled: Boolean(loadedAgent.knowledge_enabled),
      });

      // Initialize selections
      setSelectedTools(effectiveToolNames(loadedAgent, loadedTools));
      setSelectedSkills(effectiveSkillNames(loadedAgent, loadedSkills));

      const initialMcpMap: Record<string, boolean> = {};
      const agentMcpServers = loadedAgent.mcp_servers || {};
      // Mark all tenant MCP servers with their agent binding state
      for (const server of mcpData.servers || []) {
        const agentEntry = agentMcpServers[server.name];
        initialMcpMap[server.name] = Boolean(agentEntry && (agentEntry.enabled ?? true));
      }
      setMcpEnabledMap(initialMcpMap);
    } catch {
      message.error('加载数字员工失败');
      navigate('/agents');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadData();
  }, [tenantId, agentId]);

  const handleSave = async () => {
    if (!agent || !agentId) return;
    try {
      const values = await form.validateFields();
      setSaving(true);

      // Build final mcp_servers map
      const finalMcpServers: Record<string, { enabled: boolean }> = {};
      Object.entries(mcpEnabledMap).forEach(([name, enabled]) => {
        if (enabled) {
          finalMcpServers[name] = { enabled: true };
        }
      });

      const payload = formatAgentPayload({
        ...agent,
        name: values.name,
        model_config_id: values.model_config_id,
        system_prompt: values.system_prompt,
        knowledge_enabled: values.knowledge_enabled,
        tools: selectedTools,
        skills: selectedSkills,
        mcp_servers: finalMcpServers,
        metadata: {
          ...(agent.metadata || {}),
          position: values.position,
          role_intro: values.role_intro,
        },
      });

      await api.updateAgent(agentId, payload);
      message.success('已保存修改');
      await loadData();
    } catch {
      message.error('保存失败，请检查表单');
    } finally {
      setSaving(false);
    }
  };

  const startChat = () => {
    if (!agent) return;
    setAgentScope(agent.agent_id);
    navigate('/chat');
  };

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '60vh' }}>
        <Spin size="large" />
      </div>
    );
  }

  if (!agent) return null;

  const agentName = displayAgentName(agent.agent_id, agent.name);
  const agentPos = (agent.metadata?.position as string) || DEFAULT_AGENT_POSITION;

  return (
    <ConsolePage
      className="agent-detail-page-wrapper"
      title={
        <Breadcrumb
          items={[
            { title: <Link to="/agents">数字员工</Link> },
            { title: agentName },
          ]}
        />
      }
      actions={
        <Space>
          <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/agents')}>
            返回列表
          </Button>
          <Button icon={<MessageOutlined />} onClick={startChat}>
            发起会话
          </Button>
          <Button type="primary" icon={<SaveOutlined />} loading={saving} onClick={handleSave}>
            保存变更
          </Button>
        </Space>
      }
    >
      <Form form={form} layout="vertical" className="agent-detail-form-container">
        {/* HERO SECTION */}
        <div className="agent-detail-full-hero">
          <div className="agent-detail-hero-info">
            <Typography.Title level={2} style={{ margin: 0 }}>{agentName}</Typography.Title>
            <Space size={12}>
              <StatusTag status="active">{agentPos}</StatusTag>
              <Typography.Text type="secondary">ID: {agent.agent_id}</Typography.Text>
            </Space>
          </div>
        </div>

        <Tabs
          activeKey={activeTab}
          onChange={setActiveTab}
          size="large"
          className="agent-detail-full-tabs"
          items={[
            {
              key: 'core',
              label: '核心配置',
              icon: <SettingOutlined />,
              children: (
                <div className="agent-core-panel-grid">
                  <Card className="agent-section-card" title="身份与模型设定">
                    <div className="agent-core-form-grid">
                      <Form.Item name="name" label="员工昵称" rules={[{ required: true, message: '请输入员工昵称' }]}>
                        <Input placeholder="例如：支付通客服" size="large" />
                      </Form.Item>
                      <Form.Item name="position" label="职位">
                        <Input placeholder="例如：AI 业务专员" size="large" />
                      </Form.Item>
                      <Form.Item name="model_config_id" label="模型" rules={[{ required: true, message: '请选择模型' }]}>
                        <Select showSearch allowClear options={modelOptions} placeholder="选择基础模型" size="large" />
                      </Form.Item>
                      <Form.Item name="role_intro" label="角色简介">
                        <Input.TextArea rows={4} placeholder="用一两句话描述角色职责和边界。" />
                      </Form.Item>
                      <Form.Item className="agent-core-full-row">
                        <div className="agent-kb-toggle-card">
                          <Space className="agent-kb-toggle-layout">
                            <div className="agent-kb-toggle-info">
                              <Typography.Text strong>启用知识库检索</Typography.Text>
                              <Typography.Text type="secondary" className="agent-kb-toggle-desc">
                                允许数字员工在回答前自动检索工作区内相关知识库文档。
                              </Typography.Text>
                            </div>
                            <Form.Item name="knowledge_enabled" valuePropName="checked" noStyle>
                              <Switch />
                            </Form.Item>
                          </Space>
                        </div>
                      </Form.Item>
                    </div>
                  </Card>

                  <Card className="agent-section-card agent-command-card" title="系统核心指令 (System Prompt)">
                    <Form.Item name="system_prompt" className="agent-system-prompt-field">
                      <Input.TextArea
                        rows={16}
                        placeholder="在此设定数字员工的深度人设、回答边界、工作流以及必须遵循的规则..."
                      />
                    </Form.Item>
                  </Card>
                </div>
              ),
            },
            {
              key: 'capabilities',
              label: `外接能力 (${selectedTools.length + selectedSkills.length})`,
              icon: <BranchesOutlined />,
              children: (
                <div className="agent-capability-stack">
                  {/* Tools Section */}
                  <Card className="agent-section-card" title={<Space><ToolOutlined />基础工具 (Tools)</Space>}>
                    {tools.length === 0 ? (
                      <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无可用的基础工具" />
                    ) : (
                      <div className="app-store-grid">
                        {tools.map((tool) => (
                          <label key={tool.name} className={`app-store-card ${selectedTools.includes(tool.name) ? 'active' : ''}`}>
                            <div className="app-store-card-header">
                              <div className="app-store-icon"><ToolOutlined /></div>
                              <Typography.Text strong className="app-store-title">{tool.name}</Typography.Text>
                              <Switch
                                size="small"
                                checked={selectedTools.includes(tool.name)}
                                onChange={(checked) => setSelectedTools((prev) => toggleListItem(prev, tool.name, checked))}
                              />
                            </div>
                            <Typography.Paragraph type="secondary" ellipsis={{ rows: 2 }} className="app-store-desc">
                              {tool.description || '无详细描述'}
                            </Typography.Paragraph>
                          </label>
                        ))}
                      </div>
                    )}
                  </Card>

                  {/* Skills Section */}
                  <Card className="agent-section-card" title={<Space><BuildOutlined />高级技能 (Skills)</Space>}>
                    {skills.length === 0 ? (
                      <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无高级技能" />
                    ) : (
                      <div className="app-store-grid">
                        {skills.map((skill) => (
                          <label key={skill.name} className={`app-store-card ${selectedSkills.includes(skill.name) ? 'active' : ''}`}>
                            <div className="app-store-card-header">
                              <div className="app-store-icon skill-icon"><BuildOutlined /></div>
                              <Typography.Text strong className="app-store-title">{skill.name}</Typography.Text>
                              <Switch
                                size="small"
                                checked={selectedSkills.includes(skill.name)}
                                onChange={(checked) => setSelectedSkills((prev) => toggleListItem(prev, skill.name, checked))}
                              />
                            </div>
                            <Typography.Paragraph type="secondary" ellipsis={{ rows: 2 }} className="app-store-desc">
                              {skill.description || '无详细描述'}
                            </Typography.Paragraph>
                          </label>
                        ))}
                      </div>
                    )}
                  </Card>

                  {/* MCP Section */}
                  <Card className="agent-section-card" title={<Space><ApiOutlined />MCP 微服务</Space>}>
                    {tenantMcpServers.length === 0 ? (
                      <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="当前租户还没有可绑定的 MCP 服务" />
                    ) : (
                      <div className="app-store-grid">
                        {tenantMcpServers.map((server) => {
                          const bound = Boolean(mcpEnabledMap[server.name]);
                          return (
                            <label key={server.name} className={`app-store-card ${bound ? 'active' : ''}`}>
                              <div className="app-store-card-header">
                                <div className="app-store-icon mcp-icon"><ApiOutlined /></div>
                                <Typography.Text strong className="app-store-title">{server.name}</Typography.Text>
                                <Switch
                                  size="small"
                                  checked={bound}
                                  onChange={(checked) => setMcpEnabledMap((prev) => ({ ...prev, [server.name]: checked }))}
                                />
                              </div>
                              <Typography.Paragraph type="secondary" ellipsis={{ rows: 2 }} className="app-store-desc">
                                {server.command ? `命令: ${server.command}` : '未配置启动命令'}
                              </Typography.Paragraph>
                            </label>
                          );
                        })}
                      </div>
                    )}
                  </Card>
                </div>
              ),
            },
            {
              key: 'memory',
              label: '长期记忆',
              icon: <DatabaseOutlined />,
              children: scope ? (
                <div className="agent-memory-shell">
                  <Typography.Paragraph type="secondary" style={{ marginBottom: 24 }}>
                    这里管理 <b>{agentName}</b> 的专属独立记忆与知识图谱。
                  </Typography.Paragraph>
                  <Tabs
                    items={[
                      {
                        key: 'memory',
                        label: '会话记忆池',
                        icon: <DatabaseOutlined />,
                        children: (
                          <MemoryPanel
                            scope={scope}
                            title="员工记忆"
                            description="查看记忆文件碎片与梦境日记。"
                            embedded
                          />
                        ),
                      },
                      {
                        key: 'knowledge',
                        label: '私有知识库',
                        icon: <BookOutlined />,
                        children: (
                          <KnowledgePanel
                            scope={scope}
                            title="员工知识库"
                            description="专属本地化知识库管理。"
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
      </Form>
    </ConsolePage>
  );
}
