import { Button, Form, Input, Modal, Popconfirm, Segmented, Select, Space, Switch, Tag, message } from 'antd';
import { useEffect, useMemo, useState } from 'react';
import { ConsolePage, DataTableShell, PageToolbar, StatusTag } from '../components/console';
import { api } from '../services/api';
import type {
  CapabilityConfigItem,
  CapabilityProviderOption,
  CapabilityTypeOption,
  ModelConfigItem,
  ModelProviderOption,
} from '../types';
import {
  apiKeyKeepValueExtra,
  capabilityFallbacks,
  capabilityProviderFallbacks,
  filterSelectOption,
  providerOptionLabel,
} from './modelConfigShared';

interface ModelFormValues {
  provider: string;
  model_name: string;
  api_key: string;
  enabled: boolean;
  is_public: boolean;
}

interface CapabilityFormValues {
  capability: string;
  provider: string;
  model_name: string;
  api_base: string;
  api_key: string;
  enabled: boolean;
  is_public: boolean;
  is_default: boolean;
  voice: string;
  image_size: string;
}

type ConfigKind = 'model' | 'capability';

function modelPayload(values: ModelFormValues, editing: ModelConfigItem | null) {
  const payload: Record<string, unknown> = {
    provider: values.provider,
    model_name: values.model_name,
    display_name: values.model_name,
    enabled: values.enabled ?? true,
    is_public: values.is_public ?? true,
  };
  if (!editing || values.api_key?.trim()) {
    payload.api_key = values.api_key || '';
  }
  return payload;
}

function capabilityPayload(values: CapabilityFormValues, editing: CapabilityConfigItem | null) {
  const metadata: Record<string, unknown> = {};
  if (supportsVoiceField(values.capability) && values.voice?.trim()) metadata.voice = values.voice.trim();
  if (supportsImageSizeField(values.capability) && values.image_size?.trim()) metadata.image_size = values.image_size.trim();
  const payload: Record<string, unknown> = {
    capability: values.capability,
    provider: values.provider,
    model_name: values.model_name,
    display_name: values.model_name,
    api_base: values.api_base || '',
    enabled: values.enabled ?? true,
    is_public: values.is_public ?? true,
    is_default: values.is_default ?? false,
    metadata,
  };
  if (!editing || values.api_key?.trim()) {
    payload.api_key = values.api_key || '';
  }
  return payload;
}

function capabilityColor(capability: string) {
  if (capability === 'image_generation') return 'magenta';
  if (capability === 'speech_to_text') return 'geekblue';
  if (capability === 'text_to_speech') return 'cyan';
  if (capability === 'multimodal') return 'purple';
  return 'blue';
}

function supportsVoiceField(capability?: string) {
  return capability === 'text_to_speech';
}

function supportsImageSizeField(capability?: string) {
  return capability === 'image_generation';
}

export default function PlatformModelsPage() {
  const [loading, setLoading] = useState(false);
  const [activeKind, setActiveKind] = useState<ConfigKind>('model');
  const [models, setModels] = useState<ModelConfigItem[]>([]);
  const [providers, setProviders] = useState<ModelProviderOption[]>([]);
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<ModelConfigItem | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [capabilityConfigs, setCapabilityConfigs] = useState<CapabilityConfigItem[]>([]);
  const [capabilities, setCapabilities] = useState<CapabilityTypeOption[]>(capabilityFallbacks);
  const [capabilityProviders, setCapabilityProviders] = useState<CapabilityProviderOption[]>(capabilityProviderFallbacks);
  const [capabilityOpen, setCapabilityOpen] = useState(false);
  const [capabilityEditing, setCapabilityEditing] = useState<CapabilityConfigItem | null>(null);
  const [capabilitySubmitting, setCapabilitySubmitting] = useState(false);
  const [form] = Form.useForm<ModelFormValues>();
  const [capabilityForm] = Form.useForm<CapabilityFormValues>();
  const selectedProvider = Form.useWatch('provider', form);
  const selectedProviderDef = providers.find((item) => item.provider === selectedProvider);
  const selectedCapability = Form.useWatch('capability', capabilityForm);
  const selectedCapabilityProviderKey = Form.useWatch('provider', capabilityForm);
  const effectiveCapabilityProviders = capabilityProviders.length ? capabilityProviders : capabilityProviderFallbacks;
  const selectedCapabilityProvider = effectiveCapabilityProviders.find((item) => item.provider === selectedCapabilityProviderKey);
  const providerOptions = providers.map((item) => ({
    label: providerOptionLabel(item),
    value: item.provider,
  }));
  const modelOptions = (selectedProviderDef?.models || []).map((model) => ({ label: model, value: model }));
  const capabilityLabels = useMemo(
    () => Object.fromEntries(capabilities.map((item) => [item.capability, item.label])),
    [capabilities],
  );
  const capabilityOptions = capabilities.map((item) => ({ label: item.label, value: item.capability }));
  const capabilityProviderOptions = effectiveCapabilityProviders
    .filter((item) => !selectedCapability || item.capabilities.includes(selectedCapability))
    .map((item) => ({ label: providerOptionLabel(item), value: item.provider }));
  const firstProviderForCapability = (capability: string) => (
    effectiveCapabilityProviders.find((item) => item.capabilities.includes(capability))?.provider || 'custom'
  );
  const defaultBaseForProvider = (provider: string) => (
    effectiveCapabilityProviders.find((item) => item.provider === provider)?.default_api_base || ''
  );

  const load = async () => {
    setLoading(true);
    try {
      const data = await api.listPlatformModels();
      setModels(data.models || []);
      setProviders(data.providers || []);
      try {
        const capabilityData = await api.listPlatformCapabilityConfigs();
        setCapabilityConfigs(capabilityData.configs || []);
        setCapabilities(capabilityData.capabilities?.length ? capabilityData.capabilities : capabilityFallbacks);
        setCapabilityProviders(capabilityData.providers?.length ? capabilityData.providers : capabilityProviderFallbacks);
      } catch {
        setCapabilityConfigs([]);
        setCapabilities(capabilityFallbacks);
        setCapabilityProviders(capabilityProviderFallbacks);
      }
    } finally {
      setLoading(false);
    }
  };

  const openCreate = () => {
    setEditing(null);
    const provider = providers[0]?.provider || 'openai';
    const modelName = providers.find((item) => item.provider === provider)?.models?.[0] || '';
    form.setFieldsValue({
      provider,
      model_name: modelName,
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
      api_key: '',
      enabled: row.enabled,
      is_public: row.is_public,
    });
    setOpen(true);
  };

  const openCapabilityCreate = () => {
    setCapabilityEditing(null);
    const capability = capabilities[0]?.capability || 'multimodal';
    const provider = firstProviderForCapability(capability);
    capabilityForm.setFieldsValue({
      capability,
      provider,
      model_name: '',
      api_base: defaultBaseForProvider(provider),
      api_key: '',
      enabled: true,
      is_public: true,
      is_default: false,
      voice: '',
      image_size: '',
    });
    setCapabilityOpen(true);
  };

  const openCapabilityEdit = (row: CapabilityConfigItem) => {
    setCapabilityEditing(row);
    capabilityForm.setFieldsValue({
      capability: row.capability,
      provider: row.provider,
      model_name: row.model_name,
      api_base: row.api_base || '',
      api_key: '',
      enabled: row.enabled,
      is_public: row.is_public,
      is_default: row.is_default,
      voice: String(row.metadata?.voice || row.metadata?.voice_id || ''),
      image_size: String(row.metadata?.image_size || ''),
    });
    setCapabilityOpen(true);
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

  const submitCapability = async () => {
    const values = await capabilityForm.validateFields();
    setCapabilitySubmitting(true);
    try {
      if (capabilityEditing) {
        await api.updatePlatformCapabilityConfig(
          capabilityEditing.capability_config_id,
          capabilityPayload(values, capabilityEditing),
        );
        message.success('平台能力已更新');
      } else {
        await api.createPlatformCapabilityConfig(capabilityPayload(values, null));
        message.success('平台能力已创建');
      }
      setCapabilityOpen(false);
      await load();
    } finally {
      setCapabilitySubmitting(false);
    }
  };

  const remove = async (row: ModelConfigItem) => {
    await api.deletePlatformModel(row.model_config_id);
    message.success('平台模型已删除');
    await load();
  };

  const removeCapability = async (row: CapabilityConfigItem) => {
    await api.deletePlatformCapabilityConfig(row.capability_config_id);
    message.success('平台能力已删除');
    await load();
  };

  useEffect(() => {
    void load();
  }, []);

  return (
    <ConsolePage
      title="平台模型"
      actions={(
        <PageToolbar>
          <Button onClick={() => void load()}>刷新</Button>
          <Button
            type="primary"
            onClick={activeKind === 'model' ? openCreate : openCapabilityCreate}
          >
            {activeKind === 'model' ? '新增平台对话模型' : '新增平台专项能力'}
          </Button>
        </PageToolbar>
      )}
    >
      <div className="tenant-models-switch">
        <Segmented
          value={activeKind}
          onChange={(value) => setActiveKind(value as ConfigKind)}
          options={[
            { label: `对话模型 (${models.length})`, value: 'model' },
            { label: `专项能力 (${capabilityConfigs.length})`, value: 'capability' },
          ]}
        />
      </div>

      {activeKind === 'model' ? (
        <DataTableShell<ModelConfigItem>
          title="平台对话模型"
          rowKey="model_config_id"
          loading={loading}
          dataSource={models}
          pagination={{ pageSize: 12 }}
          columns={[
            {
              title: '名称',
              dataIndex: 'display_name',
              render: (value: string, row) => (
                <span className="entity-title-cell">
                  <span className="entity-title-cell-main">{value || row.model_name}</span>
                  <span className="entity-title-cell-meta">{row.model_name}</span>
                </span>
              ),
            },
            { title: '模型', dataIndex: 'model_name', render: (value: string) => <Tag color="blue">{value}</Tag> },
            { title: '厂商', dataIndex: 'provider' },
            { title: '启用', dataIndex: 'enabled', render: (value: boolean) => <StatusTag status={value}>{value ? '启用' : '停用'}</StatusTag> },
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
      ) : (
        <DataTableShell<CapabilityConfigItem>
          title="平台专项能力"
          rowKey="capability_config_id"
          loading={loading}
          dataSource={capabilityConfigs}
          pagination={{ pageSize: 12 }}
          scroll={{ x: 'max-content' }}
          columns={[
            { title: '能力类型', dataIndex: 'capability', render: (value: string) => <Tag color={capabilityColor(value)}>{capabilityLabels[value] || value}</Tag> },
            { title: '模型', dataIndex: 'model_name', render: (value: string) => <Tag color="blue">{value}</Tag> },
            { title: '厂商', dataIndex: 'provider' },
            { title: 'API Base', dataIndex: 'api_base', render: (value: string) => value || <Tag>默认</Tag> },
            { title: '默认', dataIndex: 'is_default', render: (value: boolean) => (value ? <Tag color="gold">默认</Tag> : <Tag>普通</Tag>) },
            { title: '租户可见', dataIndex: 'is_public', render: (value: boolean) => (value ? <Tag color="cyan">可用</Tag> : <Tag>隐藏</Tag>) },
            { title: '启用', dataIndex: 'enabled', render: (value: boolean) => <StatusTag status={value}>{value ? '启用' : '停用'}</StatusTag> },
            { title: 'API Key', dataIndex: 'api_key_masked', render: (value: string, row) => (row.api_key_set ? value || '已设置' : <Tag>未设置</Tag>) },
            {
              title: '操作',
              render: (_, row) => (
                <Space>
                  <Button size="small" onClick={() => openCapabilityEdit(row)}>编辑</Button>
                  <Popconfirm title="确认删除该平台能力？" onConfirm={() => void removeCapability(row)}>
                    <Button size="small" danger>删除</Button>
                  </Popconfirm>
                </Space>
              ),
            },
          ]}
        />
      )}

      <Modal
        open={open}
        title={editing ? '编辑平台对话模型' : '新增平台对话模型'}
        onCancel={() => setOpen(false)}
        onOk={() => void submit()}
        confirmLoading={submitting}
        destroyOnClose
      >
        <Form form={form} layout="vertical">
          <Form.Item name="provider" label="厂商" rules={[{ required: true }]}>
            <Select
              options={providerOptions}
              showSearch
              optionFilterProp="label"
              filterOption={filterSelectOption}
              aria-label="厂商"
              disabled={Boolean(editing)}
              onChange={(value) => {
                const nextProvider = providers.find((item) => item.provider === value);
                form.setFieldValue('model_name', nextProvider?.models?.[0] || '');
              }}
            />
          </Form.Item>
          <Form.Item name="model_name" label="模型" rules={[{ required: true }]}>
            <Select options={modelOptions} showSearch optionFilterProp="label" filterOption={filterSelectOption} aria-label="模型" />
          </Form.Item>
          <Form.Item
            name="api_key"
            label="API Key"
            extra={apiKeyKeepValueExtra(editing)}
            rules={editing?.api_key_set ? [] : [{ required: true, message: '请输入 API Key' }]}
          >
            <Input.Password autoComplete="new-password" aria-label="API Key" />
          </Form.Item>
          <Space size={32}>
            <Form.Item name="enabled" label="启用" htmlFor="platform-model-enabled" valuePropName="checked">
              <Switch id="platform-model-enabled" aria-label="启用平台模型" />
            </Form.Item>
            <Form.Item name="is_public" label="租户可见" htmlFor="platform-model-public" valuePropName="checked">
              <Switch id="platform-model-public" aria-label="租户可见" />
            </Form.Item>
          </Space>
        </Form>
      </Modal>

      <Modal
        open={capabilityOpen}
        title={capabilityEditing ? '编辑平台专项能力' : '新增平台专项能力'}
        onCancel={() => setCapabilityOpen(false)}
        onOk={() => void submitCapability()}
        confirmLoading={capabilitySubmitting}
        destroyOnClose
      >
        <Form form={capabilityForm} layout="vertical">
          <Form.Item name="capability" label="能力类型" rules={[{ required: true }]}>
            <Select
              options={capabilityOptions}
              showSearch
              optionFilterProp="label"
              filterOption={filterSelectOption}
              aria-label="能力类型"
              onChange={(value) => {
                const provider = firstProviderForCapability(String(value));
                capabilityForm.setFieldsValue({
                  provider,
                  api_base: defaultBaseForProvider(provider),
                  voice: '',
                  image_size: '',
                });
              }}
            />
          </Form.Item>
          <Form.Item name="provider" label="厂商" rules={[{ required: true }]}>
            <Select
              options={capabilityProviderOptions}
              showSearch
              optionFilterProp="label"
              filterOption={filterSelectOption}
              aria-label="厂商"
              onChange={(value) => capabilityForm.setFieldValue('api_base', defaultBaseForProvider(String(value)))}
            />
          </Form.Item>
          <Form.Item name="model_name" label="Model" rules={[{ required: true }]}>
            <Input aria-label="Model" />
          </Form.Item>
          <Form.Item
            name="api_base"
            label={selectedCapabilityProvider?.custom ? 'Base URL（自定义厂商必填）' : 'Base URL'}
            rules={selectedCapabilityProvider?.custom ? [{ required: true, message: '请输入 Base URL' }] : []}
          >
            <Input aria-label="Base URL" />
          </Form.Item>
          <Form.Item
            name="api_key"
            label="API Key"
            extra={apiKeyKeepValueExtra(capabilityEditing)}
          >
            <Input.Password autoComplete="new-password" aria-label="API Key" />
          </Form.Item>
          {supportsVoiceField(selectedCapability) ? (
            <Form.Item name="voice" label="Voice / 音色">
              <Input aria-label="Voice / 音色" />
            </Form.Item>
          ) : null}
          {supportsImageSizeField(selectedCapability) ? (
            <Form.Item name="image_size" label="图片尺寸">
              <Input aria-label="图片尺寸" placeholder="1024x1024" />
            </Form.Item>
          ) : null}
          <Space size={32}>
            <Form.Item name="enabled" label="启用" htmlFor="platform-capability-enabled" valuePropName="checked">
              <Switch id="platform-capability-enabled" aria-label="启用平台能力" />
            </Form.Item>
            <Form.Item name="is_public" label="租户可见" htmlFor="platform-capability-public" valuePropName="checked">
              <Switch id="platform-capability-public" aria-label="租户可见" />
            </Form.Item>
            <Form.Item name="is_default" label="默认" htmlFor="platform-capability-default" valuePropName="checked">
              <Switch id="platform-capability-default" aria-label="默认平台能力" />
            </Form.Item>
          </Space>
        </Form>
      </Modal>
    </ConsolePage>
  );
}
