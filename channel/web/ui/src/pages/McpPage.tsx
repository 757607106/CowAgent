import {
  Alert,
  Avatar,
  Button,
  Card,
  Empty,
  Form,
  Input,
  Modal,
  Popconfirm,
  Select,
  Space,
  Spin,
  Tag,
  Typography,
  message,
} from 'antd';
import {
  ApiOutlined,
  AppstoreOutlined,
  CodeOutlined,
  DeleteOutlined,
  EditOutlined,
  EyeOutlined,
  MinusCircleOutlined,
  PlayCircleOutlined,
  PlusOutlined,
  ReloadOutlined,
  ToolOutlined,
} from '@ant-design/icons';
import { useEffect, useMemo, useState } from 'react';
import { PageTitle } from '../components/PageTitle';
import { useRuntimeScope } from '../context/runtime';
import { api } from '../services/api';
import type { AgentItem, McpServerItem, McpTestResult, McpToolItem } from '../types';

interface EnvRow {
  key?: string;
  value?: string;
}

interface ServerFormValues {
  name: string;
  command: string;
  argsText: string;
  envList: EnvRow[];
}

interface ToolState {
  loading: boolean;
  loaded: boolean;
  error?: string;
  tools: McpToolItem[];
}

interface McpServersPanelProps {
  tenantId: string;
  selectedAgentId?: string;
  selectedAgent?: AgentItem | null;
  showAgentPicker?: boolean;
  compact?: boolean;
  onAgentChanged?: () => void | Promise<void>;
}

function formatArgs(args: string[]): string {
  return args.length > 0 ? args.join(' ') : '无参数';
}

function envToRows(env: Record<string, string> | undefined): EnvRow[] {
  const entries = Object.entries(env || {});
  return entries.length > 0
    ? entries.map(([key, value]) => ({ key, value }))
    : [{ key: '', value: '' }];
}

function rowsToEnv(rows: EnvRow[] | undefined): Record<string, string> {
  const next: Record<string, string> = {};
  (rows || []).forEach((row) => {
    const key = (row.key || '').trim();
    if (!key) return;
    next[key] = row.value || '';
  });
  return next;
}

function buildAgentPayload(agent: AgentItem, mcpServers: Record<string, unknown>) {
  return {
    tenant_id: agent.tenant_id,
    name: agent.name,
    model: agent.model,
    system_prompt: agent.system_prompt,
    tools: agent.tools || [],
    skills: agent.skills || [],
    knowledge_enabled: Boolean(agent.knowledge_enabled),
    mcp_servers: mcpServers,
  };
}

export function McpServersPanel({
  tenantId,
  selectedAgentId: controlledAgentId,
  selectedAgent: controlledAgent,
  showAgentPicker = true,
  compact = false,
  onAgentChanged,
}: McpServersPanelProps) {
  const [agents, setAgents] = useState<AgentItem[]>([]);
  const [internalAgentId, setInternalAgentId] = useState('');
  const [internalAgent, setInternalAgent] = useState<AgentItem | null>(null);
  const [servers, setServers] = useState<McpServerItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<McpServerItem | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [testing, setTesting] = useState(false);
  const [quickTestingName, setQuickTestingName] = useState('');
  const [testResult, setTestResult] = useState<McpTestResult | null>(null);
  const [testViewer, setTestViewer] = useState<{ serverName: string; result: McpTestResult } | null>(null);
  const [toolStates, setToolStates] = useState<Record<string, ToolState>>({});
  const [expandedTools, setExpandedTools] = useState<Record<string, boolean>>({});
  const [schemaViewer, setSchemaViewer] = useState<{ serverName: string; tool: McpToolItem } | null>(null);
  const [form] = Form.useForm<ServerFormValues>();

  const selectedAgentId = controlledAgentId === undefined ? internalAgentId : controlledAgentId;
  const selectedAgent = controlledAgent === undefined ? internalAgent : controlledAgent;

  const loadAgents = async () => {
    const data = await api.listAgents(tenantId);
    const list = data.agents || [];
    setAgents(list);
    if (!selectedAgentId && list.length > 0 && controlledAgentId === undefined) {
      setInternalAgentId((list.find((agent) => agent.agent_id === 'default') || list[0]).agent_id);
    }
  };

  const loadAgentDetail = async (agentId: string) => {
    if (!agentId) {
      setInternalAgent(null);
      return;
    }
    const data = await api.getAgentDetail(tenantId, agentId);
    setInternalAgent(data.agent || null);
  };

  const loadServers = async (agentId = selectedAgentId) => {
    if (!agentId) {
      setServers([]);
      return;
    }
    setLoading(true);
    try {
      const data = await api.listMcpServers(agentId, tenantId);
      setServers(data.servers || []);
    } finally {
      setLoading(false);
    }
  };

  const openCreate = () => {
    setEditing(null);
    setTestResult(null);
    form.setFieldsValue({
      name: '',
      command: '',
      argsText: '',
      envList: [{ key: '', value: '' }],
    });
    setOpen(true);
  };

  const openEdit = (server: McpServerItem) => {
    setEditing(server);
    setTestResult(null);
    form.setFieldsValue({
      name: server.name,
      command: server.command,
      argsText: server.args.join(' '),
      envList: envToRows(server.env),
    });
    setOpen(true);
  };

  const normalizeFormValues = (values: ServerFormValues) => ({
    name: values.name.trim(),
    command: values.command.trim(),
    args: values.argsText.split(' ').map((item) => item.trim()).filter(Boolean),
    env: rowsToEnv(values.envList),
  });

  const runFormTest = async () => {
    const values = await form.validateFields();
    const normalized = normalizeFormValues(values);
    setTesting(true);
    try {
      const result = await api.testMcpServer({
        command: normalized.command,
        args: normalized.args,
        env: normalized.env,
      });
      setTestResult(result);
      if (result.status === 'success') {
        message.success(`连接成功，发现 ${(result.tools || []).length} 个工具`);
      }
    } catch (error) {
      const next = {
        status: 'error' as const,
        message: error instanceof Error ? error.message : '连接测试失败',
      };
      setTestResult(next);
      message.error(next.message);
    } finally {
      setTesting(false);
    }
  };

  const quickTestServer = async (server: McpServerItem) => {
    setQuickTestingName(server.name);
    try {
      const result = await api.testMcpServer({
        command: server.command,
        args: server.args,
        env: server.env,
      });
      setTestViewer({ serverName: server.name, result });
      if (result.status === 'success') {
        message.success(`连接成功，发现 ${(result.tools || []).length} 个工具`);
      }
    } catch (error) {
      setTestViewer({
        serverName: server.name,
        result: {
          status: 'error',
          message: error instanceof Error ? error.message : '连接测试失败',
        },
      });
      message.error(error instanceof Error ? error.message : '连接测试失败');
    } finally {
      setQuickTestingName('');
    }
  };

  const saveServer = async () => {
    if (!selectedAgentId) {
      message.error('请先选择智能体');
      return;
    }

    const values = await form.validateFields();
    const normalized = normalizeFormValues(values);
    if (!normalized.name) {
      message.error('服务器名称不能为空');
      return;
    }

    setSubmitting(true);
    try {
      const detail = await api.getAgentDetail(tenantId, selectedAgentId);
      const current = detail.agent;
      const mcpServers = { ...(current.mcp_servers || {}) } as Record<string, unknown>;

      if (editing && editing.name !== normalized.name) {
        delete mcpServers[editing.name];
      }

      mcpServers[normalized.name] = {
        command: normalized.command,
        args: normalized.args,
        env: normalized.env,
      };

      await api.updateAgent(selectedAgentId, buildAgentPayload(current, mcpServers));
      message.success('MCP 服务器已保存');
      setOpen(false);
      setTestResult(null);
      await onAgentChanged?.();
      await loadAgentDetail(selectedAgentId);
      await loadServers(selectedAgentId);
    } catch (error) {
      message.error(error instanceof Error ? error.message : '保存 MCP 服务器失败');
    } finally {
      setSubmitting(false);
    }
  };

  const removeServer = async (server: McpServerItem) => {
    if (!selectedAgentId) return;
    try {
      const detail = await api.getAgentDetail(tenantId, selectedAgentId);
      const current = detail.agent;
      const mcpServers = { ...(current.mcp_servers || {}) } as Record<string, unknown>;
      delete mcpServers[server.name];
      await api.updateAgent(selectedAgentId, buildAgentPayload(current, mcpServers));
      message.success('MCP 服务器已删除');
      setExpandedTools((prev) => ({ ...prev, [server.name]: false }));
      await onAgentChanged?.();
      await loadAgentDetail(selectedAgentId);
      await loadServers(selectedAgentId);
    } catch (error) {
      message.error(error instanceof Error ? error.message : '删除 MCP 服务器失败');
    }
  };

  const loadTools = async (serverName: string, force = false) => {
    if (!selectedAgentId) return;
    const currentState = toolStates[serverName];
    if (!force && currentState?.loaded && !currentState.error) {
      return;
    }
    setToolStates((prev) => ({
      ...prev,
      [serverName]: {
        loading: true,
        loaded: false,
        tools: prev[serverName]?.tools || [],
      },
    }));
    try {
      const result = await api.listMcpServerTools(serverName, selectedAgentId, tenantId);
      setToolStates((prev) => ({
        ...prev,
        [serverName]: {
          loading: false,
          loaded: true,
          tools: result.tools || [],
        },
      }));
    } catch (error) {
      setToolStates((prev) => ({
        ...prev,
        [serverName]: {
          loading: false,
          loaded: false,
          tools: [],
          error: error instanceof Error ? error.message : '加载工具失败',
        },
      }));
    }
  };

  const toggleTools = (serverName: string) => {
    const nextExpanded = !expandedTools[serverName];
    setExpandedTools((prev) => ({ ...prev, [serverName]: nextExpanded }));
    if (nextExpanded) {
      void loadTools(serverName);
    }
  };

  useEffect(() => {
    if (!showAgentPicker) return;
    setInternalAgentId('');
    void loadAgents();
  }, [tenantId, showAgentPicker]);

  useEffect(() => {
    if (!selectedAgentId) {
      setInternalAgent(null);
      setServers([]);
      return;
    }
    if (controlledAgent === undefined) {
      void loadAgentDetail(selectedAgentId);
    }
    void loadServers(selectedAgentId);
  }, [selectedAgentId, tenantId, controlledAgent]);

  const agentSummary = useMemo(() => {
    if (!selectedAgent) return null;
    return {
      toolCount: selectedAgent.tools?.length || 0,
      skillCount: selectedAgent.skills?.length || 0,
      serverCount: servers.length,
    };
  }, [selectedAgent, servers.length]);

  return (
    <div className={compact ? 'mcp-page mcp-page-embedded' : 'mcp-page'}>
      {!compact ? (
        <PageTitle
          title="MCP 服务管理"
          description="按智能体查看、测试、编辑 MCP Server，并补齐工具查看链路。"
          extra={showAgentPicker ? (
          <Space wrap>
            <Select
              style={{ width: 320 }}
              value={selectedAgentId || undefined}
              placeholder="选择智能体"
              onChange={setInternalAgentId}
              options={agents.map((agent) => ({
                label: `${agent.name} (${agent.agent_id})`,
                value: agent.agent_id,
              }))}
            />
            <Button icon={<ReloadOutlined />} onClick={() => void loadServers(selectedAgentId)} disabled={!selectedAgentId}>
              刷新
            </Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={openCreate} disabled={!selectedAgentId}>
              新增服务器
            </Button>
          </Space>
          ) : (
            <Space wrap>
              <Button icon={<ReloadOutlined />} onClick={() => void loadServers(selectedAgentId)} disabled={!selectedAgentId}>
                刷新
              </Button>
              <Button type="primary" icon={<PlusOutlined />} onClick={openCreate} disabled={!selectedAgentId}>
                新增服务器
              </Button>
            </Space>
          )}
        />
      ) : (
        <div className="mcp-embedded-toolbar">
          <Space wrap>
            <Button icon={<ReloadOutlined />} onClick={() => void loadServers(selectedAgentId)} disabled={!selectedAgentId}>
              刷新连接
            </Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={openCreate} disabled={!selectedAgentId}>
              新增连接
            </Button>
          </Space>
        </div>
      )}

      {selectedAgent ? (
        <Card className="mcp-agent-summary">
          <div className="mcp-agent-summary-header">
            <Space align="start" size={12}>
              <Avatar size={52} style={{ background: '#eef4ff', color: '#2f64ff' }} icon={<AppstoreOutlined />} />
              <div>
                <Typography.Title level={4} style={{ margin: 0 }}>
                  {selectedAgent.name}
                </Typography.Title>
                <Typography.Text type="secondary">{selectedAgent.agent_id}</Typography.Text>
                <div style={{ marginTop: 8 }}>
                  <Tag color="blue">模型：{selectedAgent.model || '未配置'}</Tag>
                  <Tag color="purple">工具 {agentSummary?.toolCount || 0}</Tag>
                  <Tag color="geekblue">技能 {agentSummary?.skillCount || 0}</Tag>
                  <Tag color="cyan">MCP Server {agentSummary?.serverCount || 0}</Tag>
                </div>
              </div>
            </Space>
            <Typography.Paragraph type="secondary" style={{ maxWidth: 480, marginBottom: 0 }}>
              当前页的所有新增、编辑、删除都会直接写回所选智能体的 `mcp_servers` 配置，并保留原有工具、技能、系统提示等设置不变。
            </Typography.Paragraph>
          </div>
        </Card>
      ) : (
        <Card>
          <Empty description="暂无可管理的智能体。" />
        </Card>
      )}

      <Card loading={loading} style={{ marginTop: 16 }}>
        {servers.length === 0 ? (
          <Empty
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            description="当前智能体还没有 MCP Server。"
          >
            <Button type="primary" icon={<PlusOutlined />} onClick={openCreate} disabled={!selectedAgentId}>
              添加第一个服务器
            </Button>
          </Empty>
        ) : (
          <Space direction="vertical" size={16} style={{ width: '100%' }}>
            {servers.map((server) => {
              const toolState = toolStates[server.name];
              const expanded = Boolean(expandedTools[server.name]);

              return (
                <Card key={server.name} className="mcp-server-card">
                  <div className="mcp-server-header">
                    <Space align="start" size={12}>
                      <Avatar style={{ background: '#f3ecff', color: '#8f53ff' }} icon={<ApiOutlined />} />
                      <div>
                        <Typography.Title level={5} style={{ margin: 0 }}>
                          {server.name}
                        </Typography.Title>
                        <Typography.Text type="secondary" style={{ fontFamily: 'monospace' }}>
                          {server.command}
                        </Typography.Text>
                        <div style={{ marginTop: 8 }}>
                          <Tag color="blue">参数：{formatArgs(server.args)}</Tag>
                          <Tag color="cyan">环境变量 {Object.keys(server.env || {}).length}</Tag>
                        </div>
                      </div>
                    </Space>

                    <Space wrap>
                      <Button
                        icon={<EyeOutlined />}
                        onClick={() => toggleTools(server.name)}
                      >
                        {expanded ? '收起工具' : '查看工具'}
                      </Button>
                      <Button
                        icon={<PlayCircleOutlined />}
                        loading={quickTestingName === server.name}
                        onClick={() => void quickTestServer(server)}
                      >
                        测试连接
                      </Button>
                      <Button icon={<EditOutlined />} onClick={() => openEdit(server)}>
                        编辑
                      </Button>
                      <Popconfirm title={`确认删除 ${server.name} 吗？`} onConfirm={() => void removeServer(server)}>
                        <Button danger icon={<DeleteOutlined />}>删除</Button>
                      </Popconfirm>
                    </Space>
                  </div>

                  {expanded ? (
                    <div className="mcp-tools-panel">
                      <div className="mcp-tools-panel-head">
                        <Typography.Text strong>运行中工具列表</Typography.Text>
                        <Button type="link" icon={<ReloadOutlined />} onClick={() => void loadTools(server.name, true)}>
                          重新发现
                        </Button>
                      </div>

                      {toolState?.loading ? (
                        <div className="mcp-tools-loading">
                          <Spin size="small" />
                          <Typography.Text type="secondary">正在查询运行中的工具列表...</Typography.Text>
                        </div>
                      ) : null}

                      {!toolState?.loading && toolState?.error ? (
                        <Alert
                          type="warning"
                          showIcon
                          message="当前无法读取工具列表"
                          description={toolState.error}
                        />
                      ) : null}

                      {!toolState?.loading && !toolState?.error && (toolState?.tools || []).length === 0 ? (
                        <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂未发现可用工具。" />
                      ) : null}

                      {!toolState?.loading && !toolState?.error && (toolState?.tools || []).length > 0 ? (
                        <div className="mcp-tool-grid">
                          {toolState.tools.map((tool) => (
                            <Card
                              key={`${server.name}-${tool.name}`}
                              size="small"
                              className="mcp-tool-card"
                              onClick={() => setSchemaViewer({ serverName: server.name, tool })}
                            >
                              <Space direction="vertical" size={6} style={{ width: '100%' }}>
                                <Space>
                                  <ToolOutlined />
                                  <Typography.Text strong style={{ fontFamily: 'monospace' }}>
                                    {tool.name}
                                  </Typography.Text>
                                </Space>
                                <Typography.Paragraph type="secondary" ellipsis={{ rows: 2 }} style={{ marginBottom: 0 }}>
                                  {tool.description || '该工具未提供描述。'}
                                </Typography.Paragraph>
                                <Button type="link" size="small" icon={<CodeOutlined />} style={{ paddingInline: 0 }}>
                                  查看输入 Schema
                                </Button>
                              </Space>
                            </Card>
                          ))}
                        </div>
                      ) : null}
                    </div>
                  ) : null}
                </Card>
              );
            })}
          </Space>
        )}
      </Card>

      <Modal
        open={open}
        title={editing ? `编辑 MCP Server：${editing.name}` : '新增 MCP Server'}
        onCancel={() => setOpen(false)}
        onOk={() => void saveServer()}
        confirmLoading={submitting}
        width={860}
        footer={(_, { OkBtn, CancelBtn }) => (
          <Space>
            <Button icon={<PlayCircleOutlined />} loading={testing} onClick={() => void runFormTest()}>
              测试连接
            </Button>
            <CancelBtn />
            <OkBtn />
          </Space>
        )}
      >
        <Form form={form} layout="vertical">
          <Form.Item name="name" label="服务器名称" rules={[{ required: true, message: '请输入服务器名称' }]}>
            <Input placeholder="filesystem" disabled={Boolean(editing)} />
          </Form.Item>
          <Form.Item name="command" label="启动命令" rules={[{ required: true, message: '请输入启动命令' }]}>
            <Input placeholder="npx" />
          </Form.Item>
          <Form.Item name="argsText" label="参数">
            <Input placeholder="-y @modelcontextprotocol/server-filesystem /tmp" />
          </Form.Item>

          <Form.List name="envList">
            {(fields, { add, remove }) => (
              <div className="mcp-env-editor">
                <div className="mcp-env-editor-head">
                  <Typography.Text strong>环境变量</Typography.Text>
                  <Button type="link" icon={<PlusOutlined />} onClick={() => add({ key: '', value: '' })}>
                    添加变量
                  </Button>
                </div>
                <Space direction="vertical" size={8} style={{ width: '100%' }}>
                  {fields.map((field) => (
                    <Space key={field.key} align="start" style={{ display: 'flex' }}>
                      <Form.Item {...field} name={[field.name, 'key']} noStyle>
                        <Input placeholder="变量名" style={{ width: 220 }} />
                      </Form.Item>
                      <Form.Item {...field} name={[field.name, 'value']} noStyle>
                        <Input placeholder="变量值" style={{ width: 340 }} />
                      </Form.Item>
                      <Button icon={<MinusCircleOutlined />} onClick={() => remove(field.name)} />
                    </Space>
                  ))}
                </Space>
              </div>
            )}
          </Form.List>
        </Form>

        {testResult ? (
          <div className="mcp-test-result">
            <Alert
              type={testResult.status === 'success' ? 'success' : 'error'}
              showIcon
              message={testResult.status === 'success'
                ? `测试成功，发现 ${(testResult.tools || []).length} 个工具`
                : testResult.message || '测试失败'}
              description={testResult.status === 'success' ? '这只是连通性测试，保存后仍需由当前智能体实际加载。' : undefined}
            />
            {testResult.status === 'success' && (testResult.tools || []).length > 0 ? (
              <div className="mcp-tool-grid" style={{ marginTop: 12 }}>
                {(testResult.tools || []).map((tool) => (
                  <Card
                    key={`test-${tool.name}`}
                    size="small"
                    className="mcp-tool-card"
                    onClick={() => setSchemaViewer({ serverName: editing?.name || 'test', tool })}
                  >
                    <Space direction="vertical" size={4} style={{ width: '100%' }}>
                      <Typography.Text strong style={{ fontFamily: 'monospace' }}>
                        {tool.name}
                      </Typography.Text>
                      <Typography.Paragraph type="secondary" ellipsis={{ rows: 2 }} style={{ marginBottom: 0 }}>
                        {tool.description || '该工具未提供描述。'}
                      </Typography.Paragraph>
                    </Space>
                  </Card>
                ))}
              </div>
            ) : null}
          </div>
        ) : null}
      </Modal>

      <Modal
        open={Boolean(testViewer)}
        title={testViewer ? `测试结果：${testViewer.serverName}` : '测试结果'}
        footer={null}
        onCancel={() => setTestViewer(null)}
        width={820}
      >
        {testViewer ? (
          <>
            <Alert
              type={testViewer.result.status === 'success' ? 'success' : 'error'}
              showIcon
              message={testViewer.result.status === 'success'
                ? `连接成功，发现 ${(testViewer.result.tools || []).length} 个工具`
                : testViewer.result.message || '连接失败'}
            />
            {testViewer.result.status === 'success' && (testViewer.result.tools || []).length > 0 ? (
              <div className="mcp-tool-grid" style={{ marginTop: 12 }}>
                {(testViewer.result.tools || []).map((tool) => (
                  <Card
                    key={`viewer-${tool.name}`}
                    size="small"
                    className="mcp-tool-card"
                    onClick={() => setSchemaViewer({ serverName: testViewer.serverName, tool })}
                  >
                    <Space direction="vertical" size={4} style={{ width: '100%' }}>
                      <Typography.Text strong style={{ fontFamily: 'monospace' }}>
                        {tool.name}
                      </Typography.Text>
                      <Typography.Paragraph type="secondary" ellipsis={{ rows: 2 }} style={{ marginBottom: 0 }}>
                        {tool.description || '该工具未提供描述。'}
                      </Typography.Paragraph>
                    </Space>
                  </Card>
                ))}
              </div>
            ) : null}
          </>
        ) : null}
      </Modal>

      <Modal
        open={Boolean(schemaViewer)}
        title={schemaViewer ? `${schemaViewer.serverName} / ${schemaViewer.tool.name}` : '工具 Schema'}
        footer={null}
        onCancel={() => setSchemaViewer(null)}
        width={880}
      >
        {schemaViewer ? (
          <Space direction="vertical" size={12} style={{ width: '100%' }}>
            <Alert
              type="info"
              showIcon
              message={schemaViewer.tool.description || '该工具未提供描述。'}
            />
            <pre className="mcp-schema-block">
              {JSON.stringify(schemaViewer.tool.inputSchema || {}, null, 2)}
            </pre>
          </Space>
        ) : null}
      </Modal>
    </div>
  );
}

export default function McpPage() {
  const { tenantId } = useRuntimeScope();
  return <McpServersPanel tenantId={tenantId} />;
}
