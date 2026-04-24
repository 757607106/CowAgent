import { Button, Card, Form, Input, Modal, Popconfirm, Select, Space, Switch, Table, Tag, message } from 'antd';
import { useEffect, useMemo, useState } from 'react';
import { JsonBlock } from '../components/JsonBlock';
import { PageTitle } from '../components/PageTitle';
import { useRuntimeScope } from '../context/runtime';
import { api, formatAgentPayload } from '../services/api';
import type { AgentItem, SkillItem, TenantItem, ToolItem } from '../types';

interface AgentFormValues {
  tenant_id: string;
  agent_id: string;
  name: string;
  model: string | string[];
  system_prompt: string;
  tools: string[];
  skills: string[];
  knowledge_enabled: boolean;
}

function firstValue(input: string | string[] | undefined): string {
  if (Array.isArray(input)) return input[0] || '';
  return input || '';
}

export default function AgentsPage() {
  const { tenantId: currentTenantId, refreshAgentOptions } = useRuntimeScope();
  const [loading, setLoading] = useState(false);
  const [tenants, setTenants] = useState<TenantItem[]>([]);
  const [tenantId, setTenantId] = useState(currentTenantId);
  const [agents, setAgents] = useState<AgentItem[]>([]);
  const [tools, setTools] = useState<ToolItem[]>([]);
  const [skills, setSkills] = useState<SkillItem[]>([]);
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<AgentItem | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [form] = Form.useForm<AgentFormValues>();

  const models = useMemo(() => Array.from(new Set(agents.map((a) => a.model).filter(Boolean))), [agents]);
  const tenantNameById = useMemo(
    () => new Map(tenants.map((tenant) => [tenant.tenant_id, tenant.name])),
    [tenants],
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

  const loadCapabilities = async (tenant = tenantId) => {
    const [toolData, skillData] = await Promise.all([
      api.listTools(),
      api.listSkills({ tenantId: tenant, agentId: '', bindingId: '' }),
    ]);
    setTools(toolData.tools || []);
    setSkills(skillData.skills || []);
  };

  const openCreate = () => {
    setEditing(null);
    form.setFieldsValue({
      tenant_id: tenantId,
      agent_id: '',
      name: '',
      model: '',
      system_prompt: '',
      tools: [],
      skills: [],
      knowledge_enabled: false,
    });
    setOpen(true);
  };

  const openEdit = (row: AgentItem) => {
    setEditing(row);
    form.setFieldsValue({
      tenant_id: row.tenant_id,
      agent_id: row.agent_id,
      name: row.name,
      model: row.model,
      system_prompt: row.system_prompt || '',
      tools: row.tools || [],
      skills: row.skills || [],
      knowledge_enabled: Boolean(row.knowledge_enabled),
    });
    setOpen(true);
  };

  const onSubmit = async () => {
    const values = await form.validateFields();
    const effectiveTenantId = values.tenant_id || tenantId || currentTenantId;
    const payload = formatAgentPayload({
      tenant_id: effectiveTenantId,
      agent_id: editing ? values.agent_id || editing.agent_id : undefined,
      name: values.name,
      model: firstValue(values.model),
      system_prompt: values.system_prompt,
      tools: values.tools || [],
      skills: values.skills || [],
      knowledge_enabled: values.knowledge_enabled,
      mcp_servers: editing?.mcp_servers || {},
    });

    setSubmitting(true);
    try {
      if (editing) {
        await api.updateAgent(editing.agent_id, payload);
        message.success('智能体已更新');
      } else {
        await api.createAgent(payload);
        message.success('智能体已创建');
      }
      setOpen(false);
      await loadAgents(effectiveTenantId);
      await refreshAgentOptions();
    } finally {
      setSubmitting(false);
    }
  };

  const onDelete = async (row: AgentItem) => {
    await api.deleteAgent(row.tenant_id, row.agent_id);
    message.success('智能体已删除');
    await loadAgents(row.tenant_id);
    await refreshAgentOptions();
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
    <Card>
      <PageTitle
        title="智能体管理"
        description="管理租户下的 Agent、模型与能力配置。"
        extra={(
          <Space>
            <Select
              value={tenantId}
              style={{ width: 200 }}
              onChange={(value) => setTenantId(value)}
              options={(tenants.length > 0 ? tenants : [{ tenant_id: 'default', name: 'default' }]).map((tenant) => ({
                label: tenant.name,
                value: tenant.tenant_id,
              }))}
            />
            <Button onClick={() => void loadAgents(tenantId)}>刷新</Button>
            <Button type="primary" onClick={openCreate}>新建智能体</Button>
          </Space>
        )}
      />
      <Table<AgentItem>
        rowKey={(row) => `${row.tenant_id}/${row.agent_id}`}
        loading={loading}
        dataSource={agents}
        pagination={{ pageSize: 20 }}
        columns={[
          { title: '名称', dataIndex: 'name' },
          { title: '租户', dataIndex: 'tenant_id', render: (value: string) => tenantNameById.get(value) || value },
          { title: '模型', dataIndex: 'model', render: (v: string) => (v ? <Tag color="blue">{v}</Tag> : '-') },
          { title: '工具数', render: (_, row) => row.tools?.length || 0 },
          { title: '技能数', render: (_, row) => row.skills?.length || 0 },
          { title: '知识库', render: (_, row) => (row.knowledge_enabled ? <Tag color="green">开启</Tag> : <Tag>关闭</Tag>) },
          {
            title: '操作',
            render: (_, row) => (
              <Space>
                <Button size="small" onClick={() => openEdit(row)}>编辑</Button>
                <Popconfirm title="确认删除该智能体？" onConfirm={() => void onDelete(row)}>
                  <Button size="small" danger>删除</Button>
                </Popconfirm>
              </Space>
            ),
          },
        ]}
        expandable={{
          expandedRowRender: (row) => <JsonBlock value={row} />,
        }}
      />

      <Modal
        open={open}
        title={editing ? '编辑智能体' : '新建智能体'}
        onCancel={() => setOpen(false)}
        onOk={() => void onSubmit()}
        confirmLoading={submitting}
        width={760}
        destroyOnClose
      >
        <Form form={form} layout="vertical">
          <Form.Item name="name" label="名称" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="model" label="模型" rules={[{ required: true }]}>
            <Select
              showSearch
              allowClear
              options={models.map((model) => ({ label: model, value: model }))}
              placeholder="可直接输入"
              mode="tags"
              maxCount={1}
            />
          </Form.Item>
          <Form.Item name="system_prompt" label="系统提示词">
            <Input.TextArea rows={4} />
          </Form.Item>
          <Form.Item name="tools" label="工具">
            <Select
              mode="multiple"
              allowClear
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
              options={skills.map((skill) => ({
                label: skill.description ? `${skill.name} - ${skill.description}` : skill.name,
                value: skill.name,
              }))}
              placeholder="选择技能"
            />
          </Form.Item>
          <Form.Item name="knowledge_enabled" label="启用知识库" valuePropName="checked">
            <Switch />
          </Form.Item>
        </Form>
      </Modal>
    </Card>
  );
}
