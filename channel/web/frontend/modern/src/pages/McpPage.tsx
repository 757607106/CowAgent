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
  Space,
  Spin,
  Tag,
  Typography,
  message,
} from 'antd';
import {
  ApiOutlined,
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
import { useEffect, useState } from 'react';
import { ConsolePage, PageToolbar } from '../components/console';
import { useRuntimeScope } from '../context/runtime';
import { api } from '../services/api';
import type { McpServerItem, McpTestResult, McpToolItem } from '../types';

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
  compact?: boolean;
  onAgentChanged?: () => void | Promise<void>;
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

export function McpServersPanel({
  tenantId,
  compact = false,
  onAgentChanged,
}: McpServersPanelProps) {
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

  const loadServers = async () => {
    setLoading(true);
    try {
      const data = await api.listMcpServers(tenantId);
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
    args: values.argsText.match(/\S+/g) ?? [],
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
    const values = await form.validateFields();
    const normalized = normalizeFormValues(values);
    if (!normalized.name) {
      message.error('服务器名称不能为空');
      return;
    }

    setSubmitting(true);
    try {
      const payload = {
        name: normalized.name,
        command: normalized.command,
        args: normalized.args,
        env: normalized.env,
        enabled: true,
      };

      if (editing) {
        await api.updateMcpServer(tenantId, editing.name, payload);
      } else {
        await api.createMcpServer(tenantId, payload);
      }
      message.success('MCP 服务器已保存');
      setOpen(false);
      setTestResult(null);
      await onAgentChanged?.();
      await loadServers();
    } catch (error) {
      message.error(error instanceof Error ? error.message : '保存 MCP 服务器失败');
    } finally {
      setSubmitting(false);
    }
  };

  const removeServer = async (server: McpServerItem) => {
    try {
      await api.deleteMcpServer(tenantId, server.name);
      message.success('MCP 服务器已删除');
      setExpandedTools((prev) => ({ ...prev, [server.name]: false }));
      await onAgentChanged?.();
      await loadServers();
    } catch (error) {
      message.error(error instanceof Error ? error.message : '删除 MCP 服务器失败');
    }
  };

  const loadTools = async (serverName: string, force = false) => {
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
      const result = await api.listMcpServerTools(serverName, tenantId);
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
    void loadServers();
  }, [tenantId]);

  const pageBody = (
    <>
      {!compact ? (
        null
      ) : (
        <div className="mcp-embedded-toolbar">
          <Space wrap>
            <Button icon={<ReloadOutlined />} onClick={() => void loadServers()}>
              刷新连接
            </Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
              新增连接
            </Button>
          </Space>
        </div>
      )}

      <Card loading={loading} className="mcp-server-list-card">
        {servers.length === 0 ? (
          <Empty
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            description="当前租户还没有 MCP Server。"
          >
            <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
              添加第一个服务器
            </Button>
          </Empty>
        ) : (
          <div className="mcp-server-list">
            {servers.map((server) => {
              const toolState = toolStates[server.name];
              const expanded = Boolean(expandedTools[server.name]);

              return (
                <Card key={server.name} className="mcp-server-card">
                  <div className="mcp-server-header">
                    <Space align="start" size={12}>
                      <Avatar className="mcp-server-avatar" icon={<ApiOutlined />} />
                      <div>
                        <Typography.Title level={5} className="mcp-server-title">
                          {server.name}
                        </Typography.Title>
                        <Typography.Text type="secondary">
                          启动命令已配置
                        </Typography.Text>
                        <div className="mcp-server-tags">
                          <Tag color="blue">参数 {server.args.length}</Tag>
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
                          title="当前无法读取工具列表"
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
                              <div className="mcp-tool-card-body">
                                <Space>
                                  <ToolOutlined />
                                  <Typography.Text strong className="technical-id">
                                    {tool.name}
                                  </Typography.Text>
                                </Space>
                                <Typography.Paragraph type="secondary" ellipsis={{ rows: 2 }} className="compact-paragraph">
                                  {tool.description || '该工具未提供描述。'}
                                </Typography.Paragraph>
                                <Button type="link" size="small" icon={<CodeOutlined />} className="inline-link-button">
                                  查看输入 Schema
                                </Button>
                              </div>
                            </Card>
                          ))}
                        </div>
                      ) : null}
                    </div>
                  ) : null}
                </Card>
              );
            })}
          </div>
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
            <Input placeholder="filesystem" disabled={Boolean(editing)} aria-label="服务器名称" />
          </Form.Item>
          <Form.Item name="command" label="启动命令" rules={[{ required: true, message: '请输入启动命令' }]}>
            <Input placeholder="npx" aria-label="启动命令" />
          </Form.Item>
          <Form.Item name="argsText" label="参数" htmlFor="mcp-args"><Input id="mcp-args" placeholder="-y @modelcontextprotocol/server-filesystem /tmp" aria-label="参数" /></Form.Item>

          <Form.List name="envList">
            {(fields, { add, remove }) => (
              <div className="mcp-env-editor">
                <div className="mcp-env-editor-head">
                  <Typography.Text strong>环境变量</Typography.Text>
                  <Button type="link" icon={<PlusOutlined />} onClick={() => add({ key: '', value: '' })}>
                    添加变量
                  </Button>
                </div>
                <Space vertical size={8} className="full-width-stack">
                  {fields.map((field) => (
                    <div key={field.key} className="mcp-env-row">
                      <Form.Item {...field} name={[field.name, 'key']} label="变量名" colon={false} className="mcp-env-key">
                        <Input placeholder="变量名" />
                      </Form.Item>
                      <Form.Item {...field} name={[field.name, 'value']} label="变量值" colon={false} className="mcp-env-value">
                        <Input placeholder="变量值" />
                      </Form.Item>
                      <Button icon={<MinusCircleOutlined />} onClick={() => remove(field.name)} aria-label="删除环境变量" />
                    </div>
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
              title={testResult.status === 'success'
                ? `测试成功，发现 ${(testResult.tools || []).length} 个工具`
                : testResult.message || '测试失败'}
              description={testResult.status === 'success' ? '这只是连通性测试，保存后可在 AI 员工详情页绑定使用。' : undefined}
            />
            {testResult.status === 'success' && (testResult.tools || []).length > 0 ? (
              <div className="mcp-tool-grid mcp-tool-grid-spaced">
                {(testResult.tools || []).map((tool) => (
                  <Card
                    key={`test-${tool.name}`}
                    size="small"
                    className="mcp-tool-card"
                    onClick={() => setSchemaViewer({ serverName: editing?.name || 'test', tool })}
                  >
                    <Space vertical size={4} className="full-width-stack">
                      <Typography.Text strong className="technical-id">
                        {tool.name}
                      </Typography.Text>
                      <Typography.Paragraph type="secondary" ellipsis={{ rows: 2 }} className="compact-paragraph">
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
              title={testViewer.result.status === 'success'
                ? `连接成功，发现 ${(testViewer.result.tools || []).length} 个工具`
                : testViewer.result.message || '连接失败'}
            />
            {testViewer.result.status === 'success' && (testViewer.result.tools || []).length > 0 ? (
              <div className="mcp-tool-grid mcp-tool-grid-spaced">
                {(testViewer.result.tools || []).map((tool) => (
                  <Card
                    key={`viewer-${tool.name}`}
                    size="small"
                    className="mcp-tool-card"
                    onClick={() => setSchemaViewer({ serverName: testViewer.serverName, tool })}
                  >
                    <Space vertical size={4} className="full-width-stack">
                      <Typography.Text strong className="technical-id">
                        {tool.name}
                      </Typography.Text>
                      <Typography.Paragraph type="secondary" ellipsis={{ rows: 2 }} className="compact-paragraph">
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
          <Space vertical size={12} className="full-width-stack">
            <Alert
              type="info"
              showIcon
              title={schemaViewer.tool.description || '该工具未提供描述。'}
            />
            <pre className="mcp-schema-block">
              {JSON.stringify(schemaViewer.tool.inputSchema || {}, null, 2)}
            </pre>
          </Space>
        ) : null}
      </Modal>
    </>
  );

  if (compact) {
    return <div className="mcp-page mcp-page-embedded">{pageBody}</div>;
  }

  return (
    <ConsolePage
      className="mcp-page"
      title="MCP 服务管理"
      actions={(
        <PageToolbar>
          <Button icon={<ReloadOutlined />} onClick={() => void loadServers()}>
            刷新
          </Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
            新增服务器
          </Button>
        </PageToolbar>
      )}
    >
      {pageBody}
    </ConsolePage>
  );
}

export default function McpPage() {
  const { tenantId } = useRuntimeScope();
  return <McpServersPanel tenantId={tenantId} />;
}
