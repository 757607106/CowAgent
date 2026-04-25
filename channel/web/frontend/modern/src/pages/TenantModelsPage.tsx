import { Button, Form, Input, Modal, Popconfirm, Space, Switch, Table, Tabs, Tag, message } from 'antd';
import { useEffect, useMemo, useState } from 'react';
import { PageTitle } from '../components/PageTitle';
import { useRuntimeScope } from '../context/runtime';
import { api } from '../services/api';
import type { ModelConfigItem } from '../types';

interface ModelFormValues {
  model_name: string;
  api_base: string;
  api_key: string;
  enabled: boolean;
}

function modelPayload(values: ModelFormValues, editing: ModelConfigItem | null) {
  const payload: Record<string, unknown> = {
    provider: 'custom',
    model_name: values.model_name,
    display_name: values.model_name,
    api_base: values.api_base || '',
    enabled: values.enabled ?? true,
  };
  if (!editing || values.api_key?.trim()) {
    payload.api_key = values.api_key || '';
  }
  return payload;
}

export default function TenantModelsPage() {
  const { tenantId, authUser } = useRuntimeScope();
  const canManage = authUser?.role === 'owner' || authUser?.role === 'admin';
  const [loading, setLoading] = useState(false);
  const [availableModels, setAvailableModels] = useState<ModelConfigItem[]>([]);
  const [tenantModels, setTenantModels] = useState<ModelConfigItem[]>([]);
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<ModelConfigItem | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [form] = Form.useForm<ModelFormValues>();

  const platformModels = useMemo(
    () => availableModels.filter((model) => model.scope === 'platform'),
    [availableModels],
  );

  const load = async () => {
    setLoading(true);
    try {
      const [availableData, tenantData] = await Promise.all([
        api.listAvailableModels(tenantId),
        api.listTenantModels(tenantId),
      ]);
      setAvailableModels(availableData.models || []);
      setTenantModels(tenantData.models || []);
    } finally {
      setLoading(false);
    }
  };

  const openCreate = () => {
    setEditing(null);
    form.setFieldsValue({
      model_name: '',
      api_base: '',
      api_key: '',
      enabled: true,
    });
    setOpen(true);
  };

  const openEdit = (row: ModelConfigItem) => {
    setEditing(row);
    form.setFieldsValue({
      model_name: row.model_name,
      api_base: row.api_base || '',
      api_key: '',
      enabled: row.enabled,
    });
    setOpen(true);
  };

  const submit = async () => {
    const values = await form.validateFields();
    setSubmitting(true);
    try {
      if (editing) {
        await api.updateTenantModel(editing.model_config_id, modelPayload(values, editing));
        message.success('租户模型已更新');
      } else {
        await api.createTenantModel({ ...modelPayload(values, null), tenant_id: tenantId });
        message.success('租户模型已创建');
      }
      setOpen(false);
      await load();
    } finally {
      setSubmitting(false);
    }
  };

  const remove = async (row: ModelConfigItem) => {
    await api.deleteTenantModel(row.model_config_id);
    message.success('租户模型已删除');
    await load();
  };

  useEffect(() => {
    void load();
  }, [tenantId]);

  const columns = [
    { title: '名称', dataIndex: 'display_name', render: (value: string, row: ModelConfigItem) => value || row.model_name },
    { title: '模型', dataIndex: 'model_name', render: (value: string) => <Tag color="blue">{value}</Tag> },
    { title: '厂商', dataIndex: 'provider' },
    { title: '来源', dataIndex: 'scope', render: (value: string) => (value === 'platform' ? <Tag color="purple">平台</Tag> : <Tag color="cyan">本租户</Tag>) },
    { title: '启用', dataIndex: 'enabled', render: (value: boolean) => (value ? <Tag color="green">启用</Tag> : <Tag>停用</Tag>) },
    { title: 'API Key', dataIndex: 'api_key_masked', render: (value: string, row: ModelConfigItem) => (row.api_key_set ? value || '已设置' : <Tag>未设置</Tag>) },
  ];

  return (
    <div>
      <PageTitle
        title="租户模型"
        description="查看平台模型，并维护本租户自己的自定义模型接入。"
        extra={(
          <Space>
            <Button onClick={() => void load()}>刷新</Button>
            {canManage && <Button type="primary" onClick={openCreate}>新增租户模型</Button>}
          </Space>
        )}
      />
      <Tabs
        items={[
          {
            key: 'available',
            label: `可用模型 (${availableModels.length})`,
            children: (
              <Table<ModelConfigItem>
                rowKey="model_config_id"
                loading={loading}
                dataSource={availableModels}
                pagination={{ pageSize: 12 }}
                columns={columns}
              />
            ),
          },
          {
            key: 'platform',
            label: `平台模型 (${platformModels.length})`,
            children: (
              <Table<ModelConfigItem>
                rowKey="model_config_id"
                loading={loading}
                dataSource={platformModels}
                pagination={{ pageSize: 12 }}
                columns={columns}
              />
            ),
          },
          {
            key: 'tenant',
            label: `自有模型 (${tenantModels.length})`,
            children: (
              <Table<ModelConfigItem>
                rowKey="model_config_id"
                loading={loading}
                dataSource={tenantModels}
                pagination={{ pageSize: 12 }}
                columns={[
                  ...columns,
                  { title: 'API Base', dataIndex: 'api_base', render: (value: string) => value || <Tag>未设置</Tag> },
                  {
                    title: '操作',
                    render: (_: unknown, row: ModelConfigItem) => canManage ? (
                      <Space>
                        <Button size="small" onClick={() => openEdit(row)}>编辑</Button>
                        <Popconfirm title="确认删除该租户模型？" onConfirm={() => void remove(row)}>
                          <Button size="small" danger>删除</Button>
                        </Popconfirm>
                      </Space>
                    ) : null,
                  },
                ]}
              />
            ),
          },
        ]}
      />

      <Modal
        open={open}
        title={editing ? '编辑租户模型' : '新增租户模型'}
        onCancel={() => setOpen(false)}
        onOk={() => void submit()}
        confirmLoading={submitting}
        destroyOnClose
      >
        <Form form={form} layout="vertical">
          <Form.Item name="model_name" label="模型名称" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="api_base" label="API Base" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item
            name="api_key"
            label={editing?.api_key_set ? `API Key（留空保持 ${editing.api_key_masked || '当前值'}）` : 'API Key'}
          >
            <Input.Password autoComplete="new-password" />
          </Form.Item>
          <Form.Item name="enabled" label="启用" valuePropName="checked">
            <Switch />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
