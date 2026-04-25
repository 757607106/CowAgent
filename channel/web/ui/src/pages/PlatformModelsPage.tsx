import { Button, Form, Input, Modal, Popconfirm, Select, Space, Switch, Table, Tag, message } from 'antd';
import { useEffect, useState } from 'react';
import { PageTitle } from '../components/PageTitle';
import { api } from '../services/api';
import type { ModelConfigItem } from '../types';

const PROVIDERS = [
  'openai',
  'deepseek',
  'dashscope',
  'zhipu',
  'moonshot',
  'doubao',
  'claudeAPI',
  'gemini',
  'minimax',
  'modelscope',
  'linkai',
].map((provider) => ({ label: provider, value: provider }));

interface ModelFormValues {
  provider: string;
  model_name: string;
  display_name: string;
  api_base: string;
  api_key: string;
  enabled: boolean;
  is_public: boolean;
}

function modelPayload(values: ModelFormValues, editing: ModelConfigItem | null) {
  const payload: Record<string, unknown> = {
    provider: values.provider,
    model_name: values.model_name,
    display_name: values.display_name || values.model_name,
    api_base: values.api_base || '',
    enabled: values.enabled ?? true,
    is_public: values.is_public ?? true,
  };
  if (!editing || values.api_key?.trim()) {
    payload.api_key = values.api_key || '';
  }
  return payload;
}

export default function PlatformModelsPage() {
  const [loading, setLoading] = useState(false);
  const [models, setModels] = useState<ModelConfigItem[]>([]);
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<ModelConfigItem | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [form] = Form.useForm<ModelFormValues>();

  const load = async () => {
    setLoading(true);
    try {
      const data = await api.listPlatformModels();
      setModels(data.models || []);
    } finally {
      setLoading(false);
    }
  };

  const openCreate = () => {
    setEditing(null);
    form.setFieldsValue({
      provider: 'openai',
      model_name: '',
      display_name: '',
      api_base: '',
      api_key: '',
      enabled: true,
      is_public: true,
    });
    setOpen(true);
  };

  const openEdit = (row: ModelConfigItem) => {
    setEditing(row);
    form.setFieldsValue({
      provider: row.provider,
      model_name: row.model_name,
      display_name: row.display_name || row.model_name,
      api_base: row.api_base || '',
      api_key: '',
      enabled: row.enabled,
      is_public: row.is_public,
    });
    setOpen(true);
  };

  const submit = async () => {
    const values = await form.validateFields();
    setSubmitting(true);
    try {
      if (editing) {
        await api.updatePlatformModel(editing.model_config_id, modelPayload(values, editing));
        message.success('平台模型已更新');
      } else {
        await api.createPlatformModel(modelPayload(values, null));
        message.success('平台模型已创建');
      }
      setOpen(false);
      await load();
    } finally {
      setSubmitting(false);
    }
  };

  const remove = async (row: ModelConfigItem) => {
    await api.deletePlatformModel(row.model_config_id);
    message.success('平台模型已删除');
    await load();
  };

  useEffect(() => {
    void load();
  }, []);

  return (
    <div>
      <PageTitle
        title="平台模型"
        description="配置平台统一提供给租户使用的模型。"
        extra={(
          <Space>
            <Button onClick={() => void load()}>刷新</Button>
            <Button type="primary" onClick={openCreate}>新增模型</Button>
          </Space>
        )}
      />
      <Table<ModelConfigItem>
        rowKey="model_config_id"
        loading={loading}
        dataSource={models}
        pagination={{ pageSize: 12 }}
        columns={[
          { title: '名称', dataIndex: 'display_name', render: (value: string, row) => value || row.model_name },
          { title: '模型', dataIndex: 'model_name', render: (value: string) => <Tag color="blue">{value}</Tag> },
          { title: '厂商', dataIndex: 'provider' },
          { title: '启用', dataIndex: 'enabled', render: (value: boolean) => (value ? <Tag color="green">启用</Tag> : <Tag>停用</Tag>) },
          { title: '租户可见', dataIndex: 'is_public', render: (value: boolean) => (value ? <Tag color="cyan">可用</Tag> : <Tag>隐藏</Tag>) },
          { title: 'API Key', dataIndex: 'api_key_masked', render: (value: string, row) => (row.api_key_set ? value || '已设置' : <Tag>未设置</Tag>) },
          {
            title: '操作',
            render: (_, row) => (
              <Space>
                <Button size="small" onClick={() => openEdit(row)}>编辑</Button>
                <Popconfirm title="确认删除该平台模型？" onConfirm={() => void remove(row)}>
                  <Button size="small" danger>删除</Button>
                </Popconfirm>
              </Space>
            ),
          },
        ]}
      />

      <Modal
        open={open}
        title={editing ? '编辑平台模型' : '新增平台模型'}
        onCancel={() => setOpen(false)}
        onOk={() => void submit()}
        confirmLoading={submitting}
        destroyOnClose
      >
        <Form form={form} layout="vertical">
          <Form.Item name="provider" label="厂商" rules={[{ required: true }]}>
            <Select options={PROVIDERS} showSearch />
          </Form.Item>
          <Form.Item name="model_name" label="模型名称" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="display_name" label="展示名称">
            <Input />
          </Form.Item>
          <Form.Item name="api_base" label="API Base">
            <Input />
          </Form.Item>
          <Form.Item
            name="api_key"
            label={editing?.api_key_set ? `API Key（留空保持 ${editing.api_key_masked || '当前值'}）` : 'API Key'}
          >
            <Input.Password autoComplete="new-password" />
          </Form.Item>
          <Space size={32}>
            <Form.Item name="enabled" label="启用" valuePropName="checked">
              <Switch />
            </Form.Item>
            <Form.Item name="is_public" label="租户可见" valuePropName="checked">
              <Switch />
            </Form.Item>
          </Space>
        </Form>
      </Modal>
    </div>
  );
}
