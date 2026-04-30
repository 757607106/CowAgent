import { Button, Form, Input, Modal, Popconfirm, Segmented, Select, Space, Switch, Tag, message } from 'antd';
import { useEffect, useMemo, useState } from 'react';
import { ConsolePage, DataTableShell, PageToolbar, StatusTag } from '../components/console';
import { useRuntimeScope } from '../context/runtime';
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
  api_base: string;
  api_key: string;
  enabled: boolean;
}

interface CapabilityFormValues {
  capability: string;
  provider: string;
  model_name: string;
  api_base: string;
  api_key: string;
  enabled: boolean;
  is_default: boolean;
  voice: string;
  image_size: string;
}

type ModelScopeTab = 'platform' | 'tenant';
type ConfigKind = 'model' | 'capability';

function modelPayload(values: ModelFormValues, editing: ModelConfigItem | null) {
  const payload: Record<string, unknown> = {
    provider: values.provider,
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

export default function TenantModelsPage() {
  const { tenantId, authUser } = useRuntimeScope();
  const canManage = authUser?.role === 'owner' || authUser?.role === 'admin';
  const [loading, setLoading] = useState(false);
  const [platformModels, setPlatformModels] = useState<ModelConfigItem[]>([]);
  const [tenantModels, setTenantModels] = useState<ModelConfigItem[]>([]);
  const [modelProviders, setModelProviders] = useState<ModelProviderOption[]>([]);
  const [platformCapabilities, setPlatformCapabilities] = useState<CapabilityConfigItem[]>([]);
  const [tenantCapabilities, setTenantCapabilities] = useState<CapabilityConfigItem[]>([]);
  const [capabilities, setCapabilities] = useState<CapabilityTypeOption[]>(capabilityFallbacks);
  const [capabilityProviders, setCapabilityProviders] = useState<CapabilityProviderOption[]>(capabilityProviderFallbacks);
  const [activeScope, setActiveScope] = useState<ModelScopeTab>('platform');
  const [activeKind, setActiveKind] = useState<ConfigKind>('model');
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<ModelConfigItem | null>(null);
  const [capabilityOpen, setCapabilityOpen] = useState(false);
  const [capabilityEditing, setCapabilityEditing] = useState<CapabilityConfigItem | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [capabilitySubmitting, setCapabilitySubmitting] = useState(false);
  const [form] = Form.useForm<ModelFormValues>();
  const [capabilityForm] = Form.useForm<CapabilityFormValues>();
  const selectedModelProviderKey = Form.useWatch('provider', form);
  const selectedModelProvider = modelProviders.find((item) => item.provider === selectedModelProviderKey);
  const modelProviderOptions = modelProviders.map((item) => ({
    label: providerOptionLabel(item),
    value: item.provider,
  }));
  const modelRequiresApiBase = Boolean(selectedModelProvider?.requires_api_base || selectedModelProvider?.custom);
  const selectedCapability = Form.useWatch('capability', capabilityForm);
  const selectedCapabilityProviderKey = Form.useWatch('provider', capabilityForm);
  const effectiveCapabilityProviders = capabilityProviders.length ? capabilityProviders : capabilityProviderFallbacks;
  const selectedCapabilityProvider = effectiveCapabilityProviders.find((item) => item.provider === selectedCapabilityProviderKey);
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
  const firstModelProvider = () => modelProviders[0]?.provider || 'custom';

  const load = async () => {
    setLoading(true);
    try {
      const availableData = await api.listAvailableModels(tenantId);
      setPlatformModels((availableData.models || []).filter((model) => model.scope === 'platform'));
      const tenantData = await api.listTenantModels(tenantId);
      setTenantModels(tenantData.models || []);
      setModelProviders(tenantData.providers || []);
      try {
        const availableCapabilityData = await api.listAvailableCapabilityConfigs(tenantId);
        setPlatformCapabilities((availableCapabilityData.configs || []).filter((item) => item.scope === 'platform'));
        const tenantCapabilityData = await api.listTenantCapabilityConfigs(tenantId);
        setTenantCapabilities(tenantCapabilityData.configs || []);
        setCapabilities(tenantCapabilityData.capabilities?.length ? tenantCapabilityData.capabilities : capabilityFallbacks);
        setCapabilityProviders(tenantCapabilityData.providers?.length ? tenantCapabilityData.providers : capabilityProviderFallbacks);
      } catch {
        setPlatformCapabilities([]);
        setTenantCapabilities([]);
        setCapabilities(capabilityFallbacks);
        setCapabilityProviders(capabilityProviderFallbacks);
      }
    } finally {
      setLoading(false);
    }
  };

  const openCreate = () => {
    setEditing(null);
    const provider = firstModelProvider();
    form.setFieldsValue({
      provider,
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
      provider: row.provider,
      model_name: row.model_name,
      api_base: row.api_base || '',
      api_key: '',
      enabled: row.enabled,
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

  const submitCapability = async () => {
    const values = await capabilityForm.validateFields();
    setCapabilitySubmitting(true);
    try {
      if (capabilityEditing) {
        await api.updateTenantCapabilityConfig(
          capabilityEditing.capability_config_id,
          capabilityPayload(values, capabilityEditing),
        );
        message.success('租户能力已更新');
      } else {
        await api.createTenantCapabilityConfig({ ...capabilityPayload(values, null), tenant_id: tenantId });
        message.success('租户能力已创建');
      }
      setCapabilityOpen(false);
      await load();
    } finally {
      setCapabilitySubmitting(false);
    }
  };

  const remove = async (row: ModelConfigItem) => {
    await api.deleteTenantModel(row.model_config_id);
    message.success('租户模型已删除');
    await load();
  };

  const removeCapability = async (row: CapabilityConfigItem) => {
    await api.deleteTenantCapabilityConfig(row.capability_config_id);
    message.success('租户能力已删除');
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
    { title: '启用', dataIndex: 'enabled', render: (value: boolean) => <StatusTag status={value}>{value ? '启用' : '停用'}</StatusTag> },
    { title: 'API Key', dataIndex: 'api_key_masked', render: (value: string, row: ModelConfigItem) => (row.api_key_set ? value || '已设置' : <Tag>未设置</Tag>) },
  ];

  const tenantColumns = [
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
  ];

  const capabilityColumns = [
    { title: '能力', dataIndex: 'capability', render: (value: string) => <Tag color={capabilityColor(value)}>{capabilityLabels[value] || value}</Tag> },
    { title: '模型', dataIndex: 'model_name', render: (value: string) => <Tag color="blue">{value}</Tag> },
    { title: '厂商', dataIndex: 'provider' },
    { title: '来源', dataIndex: 'scope', render: (value: string) => (value === 'platform' ? <Tag color="purple">平台</Tag> : <Tag color="cyan">本租户</Tag>) },
    { title: '默认', dataIndex: 'is_default', render: (value: boolean) => (value ? <Tag color="gold">默认</Tag> : <Tag>普通</Tag>) },
    { title: '启用', dataIndex: 'enabled', render: (value: boolean) => <StatusTag status={value}>{value ? '启用' : '停用'}</StatusTag> },
    { title: 'API Key', dataIndex: 'api_key_masked', render: (value: string, row: CapabilityConfigItem) => (row.api_key_set ? value || '已设置' : <Tag>未设置</Tag>) },
  ];

  const tenantCapabilityColumns = [
    ...capabilityColumns,
    { title: 'API Base', dataIndex: 'api_base', render: (value: string) => value || <Tag>未设置</Tag> },
    {
      title: '操作',
      render: (_: unknown, row: CapabilityConfigItem) => canManage ? (
        <Space>
          <Button size="small" onClick={() => openCapabilityEdit(row)}>编辑</Button>
          <Popconfirm title="确认删除该租户能力？" onConfirm={() => void removeCapability(row)}>
            <Button size="small" danger>删除</Button>
          </Popconfirm>
        </Space>
      ) : null,
    },
  ];

  const activeModels = activeScope === 'platform' ? platformModels : tenantModels;
  const activeColumns = activeScope === 'platform' ? columns : tenantColumns;
  const activeCapabilities = activeScope === 'platform' ? platformCapabilities : tenantCapabilities;
  const activeCapabilityColumns = activeScope === 'platform' ? capabilityColumns : tenantCapabilityColumns;

  return (
    <ConsolePage
      title="租户模型"
      className="tenant-models-page"
      actions={(
        <PageToolbar>
          <Button onClick={() => void load()}>刷新</Button>
          {canManage && activeScope === 'tenant' ? (
            <Button
              type="primary"
              onClick={activeKind === 'model' ? openCreate : openCapabilityCreate}
            >
              {activeKind === 'model' ? '新增自有对话模型' : '新增自有专项能力'}
            </Button>
          ) : null}
        </PageToolbar>
      )}
    >
      <div className="tenant-models-switch">
        <Segmented
          value={activeScope}
          onChange={(value) => setActiveScope(value as ModelScopeTab)}
          options={[
            { label: `平台配置 (${platformModels.length + platformCapabilities.length})`, value: 'platform' },
            { label: `自有配置 (${tenantModels.length + tenantCapabilities.length})`, value: 'tenant' },
          ]}
        />
        <Segmented
          value={activeKind}
          onChange={(value) => setActiveKind(value as ConfigKind)}
          options={[
            { label: `对话模型 (${activeScope === 'platform' ? platformModels.length : tenantModels.length})`, value: 'model' },
            {
              label: `专项能力 (${activeScope === 'platform' ? platformCapabilities.length : tenantCapabilities.length})`,
              value: 'capability',
            },
          ]}
        />
      </div>

      {activeKind === 'model' ? (
        <DataTableShell<ModelConfigItem>
          className="tenant-models-table-shell"
          title={activeScope === 'platform' ? '平台对话模型' : '自有对话模型'}
          rowKey="model_config_id"
          loading={loading}
          dataSource={activeModels}
          pagination={{ pageSize: 12 }}
          locale={{ emptyText: activeScope === 'platform' ? '暂无平台对话模型' : '暂无自有对话模型' }}
          columns={activeColumns}
          scroll={{ x: 'max-content' }}
        />
      ) : (
        <DataTableShell<CapabilityConfigItem>
          className="tenant-models-table-shell"
          title={activeScope === 'platform' ? '平台专项能力' : '自有专项能力'}
          rowKey="capability_config_id"
          loading={loading}
          dataSource={activeCapabilities}
          pagination={{ pageSize: 12 }}
          locale={{ emptyText: activeScope === 'platform' ? '暂无平台专项能力' : '暂无自有专项能力' }}
          columns={activeCapabilityColumns}
          scroll={{ x: 'max-content' }}
        />
      )}

      <Modal
        open={open}
        title={editing ? '编辑自有对话模型' : '新增自有对话模型'}
        onCancel={() => setOpen(false)}
        onOk={() => void submit()}
        confirmLoading={submitting}
        destroyOnClose
      >
        <Form form={form} layout="vertical">
          <Form.Item name="provider" label="厂商" rules={[{ required: true }]}>
            <Select
              options={modelProviderOptions}
              showSearch
              optionFilterProp="label"
              filterOption={filterSelectOption}
              aria-label="厂商"
              onChange={() => form.setFieldValue('api_base', '')}
            />
          </Form.Item>
          <Form.Item name="model_name" label="Model" rules={[{ required: true }]}>
            <Input aria-label="Model" />
          </Form.Item>
          {modelRequiresApiBase ? (
            <Form.Item name="api_base" label="Base URL（自定义厂商必填）" rules={[{ required: true, message: '请输入 Base URL' }]}>
              <Input aria-label="Base URL" />
            </Form.Item>
          ) : null}
          <Form.Item
            name="api_key"
            label="API Key"
            extra={apiKeyKeepValueExtra(editing)}
          >
            <Input.Password autoComplete="new-password" aria-label="API Key" />
          </Form.Item>
          <Form.Item name="enabled" label="启用" htmlFor="tenant-model-enabled" valuePropName="checked">
            <Switch id="tenant-model-enabled" aria-label="启用租户模型" />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        open={capabilityOpen}
        title={capabilityEditing ? '编辑自有专项能力' : '新增自有专项能力'}
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
            <Form.Item name="enabled" label="启用" htmlFor="tenant-capability-enabled" valuePropName="checked">
              <Switch id="tenant-capability-enabled" aria-label="启用租户能力" />
            </Form.Item>
            <Form.Item name="is_default" label="默认" htmlFor="tenant-capability-default" valuePropName="checked">
              <Switch id="tenant-capability-default" aria-label="默认租户能力" />
            </Form.Item>
          </Space>
        </Form>
      </Modal>
    </ConsolePage>
  );
}
