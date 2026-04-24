import { Button, Card, Form, Input, Modal, Popconfirm, Select, Space, Switch, Table, Tag, message } from 'antd';
import { useEffect, useMemo, useState } from 'react';
import { JsonBlock } from '../components/JsonBlock';
import { PageTitle } from '../components/PageTitle';
import { useRuntimeScope } from '../context/runtime';
import { api, formatBindingPayload } from '../services/api';
import type { AgentItem, BindingItem, TenantItem } from '../types';

interface BindingFormValues {
  tenant_id: string;
  binding_id?: string;
  name: string;
  channel_type: string;
  agent_id: string;
  enabled: boolean;
  metadata: string;
}

export default function BindingsPage() {
  const { tenantId: currentTenantId } = useRuntimeScope();
  const [loading, setLoading] = useState(false);
  const [tenants, setTenants] = useState<TenantItem[]>([]);
  const [tenantId, setTenantId] = useState(currentTenantId);
  const [bindings, setBindings] = useState<BindingItem[]>([]);
  const [agents, setAgents] = useState<AgentItem[]>([]);
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<BindingItem | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [form] = Form.useForm<BindingFormValues>();

  const tenantAgentOptions = useMemo(() => agents.map((agent) => ({
    label: agent.name,
    value: agent.agent_id,
  })), [agents]);
  const tenantNameById = useMemo(
    () => new Map(tenants.map((tenant) => [tenant.tenant_id, tenant.name])),
    [tenants],
  );
  const agentNameById = useMemo(
    () => new Map(agents.map((agent) => [agent.agent_id, agent.name])),
    [agents],
  );

  const loadBase = async () => {
    const [tenantData, agentData] = await Promise.all([
      api.listTenants(),
      api.listAgents(tenantId || currentTenantId),
    ]);
    setTenants(tenantData.tenants || []);
    setAgents(agentData.agents || []);
  };

  const loadBindings = async () => {
    setLoading(true);
    try {
      const data = await api.listBindings(tenantId);
      setBindings(data.bindings || []);
    } finally {
      setLoading(false);
    }
  };

  const reload = async () => {
    await loadBase();
    await loadBindings();
  };

  const openCreate = () => {
    setEditing(null);
    form.setFieldsValue({
      tenant_id: tenantId || currentTenantId,
      binding_id: '',
      name: '',
      channel_type: 'web',
      agent_id: '',
      enabled: true,
      metadata: '{}',
    });
    setOpen(true);
  };

  const openEdit = (row: BindingItem) => {
    setEditing(row);
    form.setFieldsValue({
      tenant_id: row.tenant_id,
      binding_id: row.binding_id,
      name: row.name,
      channel_type: row.channel_type,
      agent_id: row.agent_id,
      enabled: Boolean(row.enabled),
      metadata: JSON.stringify(row.metadata || {}, null, 2),
    });
    setOpen(true);
  };

  const onSubmit = async () => {
    const values = await form.validateFields();
    const effectiveTenantId = values.tenant_id || tenantId || currentTenantId;
    let metadata = {};
    try {
      metadata = values.metadata ? JSON.parse(values.metadata) : {};
    } catch {
      message.error('metadata 必须是合法 JSON');
      return;
    }

    const payload = formatBindingPayload({
      tenant_id: effectiveTenantId,
      binding_id: editing ? values.binding_id : undefined,
      name: values.name,
      channel_type: values.channel_type,
      agent_id: values.agent_id,
      enabled: values.enabled,
      metadata,
    });

    setSubmitting(true);
    try {
      if (editing) {
        await api.updateBinding(editing.binding_id, payload);
        message.success('绑定已更新');
      } else {
        await api.createBinding(payload);
        message.success('绑定已创建');
      }
      setOpen(false);
      await loadBindings();
    } finally {
      setSubmitting(false);
    }
  };

  const onDelete = async (row: BindingItem) => {
    await api.deleteBinding(row.tenant_id, row.binding_id);
    message.success('绑定已删除');
    await loadBindings();
  };

  useEffect(() => {
    void reload();
  }, [tenantId]);

  useEffect(() => {
    setTenantId(currentTenantId);
  }, [currentTenantId]);

  return (
    <Card>
      <PageTitle
        title="渠道绑定管理"
        description="将渠道入口绑定到指定智能体。"
        extra={(
          <Space>
            <Select
              allowClear
              placeholder="按租户过滤"
              style={{ width: 220 }}
              value={tenantId || undefined}
              onChange={(value) => setTenantId(value || '')}
              options={tenants.map((tenant) => ({ label: tenant.name, value: tenant.tenant_id }))}
            />
            <Button onClick={() => void reload()}>刷新</Button>
            <Button type="primary" onClick={openCreate}>新建绑定</Button>
          </Space>
        )}
      />

      <Table<BindingItem>
        rowKey={(row) => `${row.tenant_id}/${row.binding_id}`}
        loading={loading}
        dataSource={bindings}
        pagination={{ pageSize: 20 }}
        columns={[
          { title: '名称', dataIndex: 'name' },
          { title: '租户', dataIndex: 'tenant_id', render: (value: string) => tenantNameById.get(value) || value },
          { title: '渠道', dataIndex: 'channel_type', render: (value: string) => <Tag color="blue">{value}</Tag> },
          { title: '智能体', dataIndex: 'agent_id', render: (value: string) => agentNameById.get(value) || value },
          { title: '启用', render: (_, row) => (row.enabled ? <Tag color="green">是</Tag> : <Tag>否</Tag>) },
          {
            title: '操作',
            render: (_, row) => (
              <Space>
                <Button size="small" onClick={() => openEdit(row)}>编辑</Button>
                <Popconfirm title="确认删除该绑定？" onConfirm={() => void onDelete(row)}>
                  <Button size="small" danger>删除</Button>
                </Popconfirm>
              </Space>
            ),
          },
        ]}
        expandable={{ expandedRowRender: (row) => <JsonBlock value={row.metadata || {}} /> }}
      />

      <Modal
        open={open}
        title={editing ? '编辑绑定' : '新建绑定'}
        onCancel={() => setOpen(false)}
        onOk={() => void onSubmit()}
        confirmLoading={submitting}
        width={760}
      >
        <Form form={form} layout="vertical">
          <Form.Item name="name" label="名称" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="channel_type" label="渠道类型" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="agent_id" label="智能体" rules={[{ required: true }]}>
            <Select
              showSearch
              allowClear
              options={tenantAgentOptions}
              placeholder="选择智能体"
            />
          </Form.Item>
          <Form.Item name="enabled" label="启用" valuePropName="checked">
            <Switch />
          </Form.Item>
          <Form.Item name="metadata" label="Metadata(JSON)">
            <Input.TextArea rows={6} />
          </Form.Item>
        </Form>
      </Modal>
    </Card>
  );
}
