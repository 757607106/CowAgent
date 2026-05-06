import { Button, Form, Input, Modal, Popconfirm, Select, Space, Switch, Tag, Typography, message } from 'antd';
import { useEffect, useMemo, useRef, useState } from 'react';
import { ConsolePage, DataTableShell, PageToolbar, StatusTag } from '../components/console';
import { useRuntimeScope } from '../context/runtime';
import { api, formatBindingPayload } from '../services/api';
import type { AgentItem, BindingItem, ChannelConfigItem, TenantItem } from '../types';

interface BindingFormValues {
  tenant_id: string;
  binding_id?: string;
  name: string;
  channel_type: string;
  channel_config_id: string;
  agent_id: string;
  enabled: boolean;
}

interface BindingsPageProps {
  embedded?: boolean;
}

const TENANT_CHANNEL_TYPES = new Set([
  'weixin',
  'feishu',
  'dingtalk',
  'wecom_bot',
  'qq',
  'wechatcom_app',
  'wechatmp',
  'wechatmp_service',
]);

function isFormValidationError(error: unknown): error is { errorFields: unknown[] } {
  return Boolean(error && typeof error === 'object' && 'errorFields' in error);
}

export default function BindingsPage({ embedded = false }: BindingsPageProps) {
  const { tenantId: currentTenantId } = useRuntimeScope();
  const [loading, setLoading] = useState(false);
  const [tenants, setTenants] = useState<TenantItem[]>([]);
  const [tenantId, setTenantId] = useState(currentTenantId);
  const [bindings, setBindings] = useState<BindingItem[]>([]);
  const [channelConfigs, setChannelConfigs] = useState<ChannelConfigItem[]>([]);
  const [agents, setAgents] = useState<AgentItem[]>([]);
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<BindingItem | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [form] = Form.useForm<BindingFormValues>();
  const selectedChannelType = Form.useWatch('channel_type', form);
  const reloadSeqRef = useRef(0);
  const bindingLoadSeqRef = useRef(0);

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
  const channelConfigById = useMemo(
    () => new Map(channelConfigs.map((config) => [config.channel_config_id, config])),
    [channelConfigs],
  );
  const channelConfigOptions = useMemo(
    () => channelConfigs
      .filter((config) => !selectedChannelType || config.channel_type === selectedChannelType)
      .map((config) => ({
        label: `${config.name} (${config.channel_type})`,
        value: config.channel_config_id,
      })),
    [channelConfigs, selectedChannelType],
  );

  const loadBindings = async (tenant = tenantId) => {
    const requestSeq = bindingLoadSeqRef.current + 1;
    bindingLoadSeqRef.current = requestSeq;
    setLoading(true);
    try {
      const data = await api.listBindings(tenant);
      if (requestSeq !== bindingLoadSeqRef.current) return;
      setBindings(data.bindings || []);
    } finally {
      if (requestSeq === bindingLoadSeqRef.current) {
        setLoading(false);
      }
    }
  };

  const reload = async () => {
    const requestSeq = reloadSeqRef.current + 1;
    reloadSeqRef.current = requestSeq;
    bindingLoadSeqRef.current = requestSeq;
    setLoading(true);
    try {
      const [tenantData, agentData, channelConfigData, bindingData] = await Promise.all([
        api.listTenants(),
        api.listAgents(tenantId || currentTenantId),
        api.listChannelConfigs(tenantId || currentTenantId),
        api.listBindings(tenantId),
      ]);
      if (requestSeq !== reloadSeqRef.current) return;
      setTenants(tenantData.tenants || []);
      setAgents(agentData.agents || []);
      setChannelConfigs(channelConfigData.channel_configs || []);
      setBindings(bindingData.bindings || []);
    } finally {
      if (requestSeq === reloadSeqRef.current) {
        setLoading(false);
      }
    }
  };

  const openCreate = () => {
    setEditing(null);
    form.resetFields();
    const defaultChannelConfig = channelConfigs[0];
    form.setFieldsValue({
      tenant_id: tenantId || currentTenantId,
      binding_id: '',
      name: '',
      channel_type: defaultChannelConfig?.channel_type || 'web',
      channel_config_id: defaultChannelConfig?.channel_config_id || '',
      agent_id: '',
      enabled: true,
    });
    setOpen(true);
  };

  const openEdit = (row: BindingItem) => {
    setEditing(row);
    form.resetFields();
    form.setFieldsValue({
      tenant_id: row.tenant_id,
      binding_id: row.binding_id,
      name: row.name,
      channel_type: row.channel_type,
      channel_config_id: row.channel_config_id || '',
      agent_id: row.agent_id,
      enabled: Boolean(row.enabled),
    });
    setOpen(true);
  };

  const validateFreshChannelConfig = async (
    effectiveTenantId: string,
    channelType: string,
    channelConfigId: string,
  ) => {
    const requiresChannelConfig = TENANT_CHANNEL_TYPES.has(channelType);
    const resolvedChannelConfigId = (channelConfigId || '').trim();

    if (!requiresChannelConfig && !resolvedChannelConfigId) {
      form.setFields([{ name: 'channel_config_id', errors: [] }]);
      return '';
    }

    if (requiresChannelConfig && !resolvedChannelConfigId) {
      const error = '租户级渠道绑定必须选择渠道配置';
      form.setFields([{ name: 'channel_config_id', errors: [error] }]);
      throw new Error(error);
    }

    const freshData = await api.listChannelConfigs(effectiveTenantId);
    const freshChannelConfigs = freshData.channel_configs || [];
    setChannelConfigs(freshChannelConfigs);

    const matchedConfig = freshChannelConfigs.find(
      (config) => config.tenant_id === effectiveTenantId
        && config.channel_config_id === resolvedChannelConfigId
        && config.channel_type === channelType,
    );
    if (!matchedConfig) {
      const error = '渠道配置不存在、已删除或不属于当前租户，请重新选择';
      form.setFieldValue('channel_config_id', '');
      form.setFields([{ name: 'channel_config_id', errors: [error] }]);
      throw new Error(error);
    }

    form.setFields([{ name: 'channel_config_id', errors: [] }]);
    return matchedConfig.channel_config_id;
  };

  const onSubmit = async () => {
    setSubmitting(true);
    try {
      const values = await form.validateFields();
      const effectiveTenantId = values.tenant_id || tenantId || currentTenantId;
      const channelConfigId = await validateFreshChannelConfig(
        effectiveTenantId,
        values.channel_type,
        values.channel_config_id,
      );

      const payload = formatBindingPayload({
        tenant_id: effectiveTenantId,
        binding_id: editing ? values.binding_id : undefined,
        name: values.name,
        channel_type: values.channel_type,
        channel_config_id: channelConfigId,
        agent_id: values.agent_id,
        enabled: values.enabled,
        metadata: editing?.metadata || {},
      });

      if (editing) {
        await api.updateBinding(editing.binding_id, payload);
        message.success('绑定已更新');
      } else {
        await api.createBinding(payload);
        message.success('绑定已创建');
      }
      setOpen(false);
      await loadBindings(effectiveTenantId);
    } catch (error) {
      if (!isFormValidationError(error)) {
        message.error(error instanceof Error ? error.message : '保存绑定失败');
      }
    } finally {
      setSubmitting(false);
    }
  };

  const onDelete = async (row: BindingItem) => {
    await api.deleteBinding(row.tenant_id, row.binding_id);
    message.success('绑定已删除');
    await loadBindings(row.tenant_id);
  };

  useEffect(() => {
    void reload();
  }, [tenantId]);

  useEffect(() => {
    setTenantId(currentTenantId);
  }, [currentTenantId]);

  const toolbar = (
    <PageToolbar align="start">
      <Select
        allowClear
        placeholder="按租户过滤"
        className="tenant-filter"
        value={tenantId || undefined}
        onChange={(value) => setTenantId(value || '')}
        options={tenants.map((tenant) => ({ label: tenant.name, value: tenant.tenant_id }))}
      />
      <Button onClick={() => void reload()}>刷新</Button>
      <Button type="primary" onClick={openCreate}>新建绑定</Button>
    </PageToolbar>
  );

  const content = (
    <>
      <DataTableShell<BindingItem>
        compact={embedded}
        className="channel-table-shell"
        title={embedded ? undefined : '绑定列表'}
        rowKey={(row) => `${row.tenant_id}/${row.binding_id}`}
        loading={loading}
        dataSource={bindings}
        pagination={{ pageSize: 20 }}
        tableLayout="fixed"
        emptyState={{
          title: '暂无渠道绑定',
          description: '创建绑定后，可把外部渠道会话路由到指定 AI 员工。',
          action: <Button type="primary" onClick={openCreate}>新建绑定</Button>,
        }}
        columns={[
          {
            title: '绑定',
            dataIndex: 'name',
            width: '18%',
            render: (value: string, row) => (
              <span className="entity-title-cell">
                <span className="entity-title-cell-main">{value}</span>
                <span className="entity-title-cell-meta">{row.binding_id}</span>
              </span>
            ),
          },
          {
            title: '租户',
            dataIndex: 'tenant_id',
            width: '18%',
            ellipsis: true,
            render: (value: string) => tenantNameById.get(value) || value,
          },
          {
            title: '渠道',
            dataIndex: 'channel_type',
            width: '14%',
            render: (value: string) => <Tag color="blue">{value}</Tag>,
          },
          {
            title: '渠道配置',
            dataIndex: 'channel_config_id',
            width: '16%',
            ellipsis: true,
            render: (value: string) => {
              if (!value) return <Typography.Text type="secondary">未关联</Typography.Text>;
              return channelConfigById.get(value)?.name || value;
            },
          },
          {
            title: 'AI 员工',
            dataIndex: 'agent_id',
            width: '14%',
            ellipsis: true,
            render: (value: string) => agentNameById.get(value) || value,
          },
          {
            title: '状态',
            width: '8%',
            render: (_, row) => <StatusTag status={Boolean(row.enabled)}>{row.enabled ? '启用' : '停用'}</StatusTag>,
          },
          {
            title: '操作',
            width: '12%',
            align: 'right',
            render: (_, row) => (
              <Space wrap size={0} className="channel-row-actions">
                <Button size="small" onClick={() => openEdit(row)}>编辑</Button>
                <Popconfirm title="确认删除该绑定？" onConfirm={() => void onDelete(row)}>
                  <Button size="small" danger>删除</Button>
                </Popconfirm>
              </Space>
            ),
          },
        ]}
      />

      <Modal
        open={open}
        title={editing ? '编辑绑定' : '新建绑定'}
        onCancel={() => setOpen(false)}
        onOk={() => void onSubmit()}
        confirmLoading={submitting}
        destroyOnClose
        width="min(47.5rem, calc(100vw - 3rem))"
      >
        <Form form={form} layout="vertical" clearOnDestroy>
          <Form.Item name="name" label="名称" rules={[{ required: true }]}>
            <Input aria-label="名称" />
          </Form.Item>
          <Form.Item name="channel_type" label="渠道类型" rules={[{ required: true }]}>
            <Select
              showSearch
              aria-label="渠道类型"
              onChange={(value) => {
                const selected = channelConfigs.find(
                  (config) => config.channel_config_id === form.getFieldValue('channel_config_id'),
                );
                if (selected && selected.channel_type !== value) {
                  form.setFieldValue('channel_config_id', '');
                }
                const sameTypeConfigs = channelConfigs.filter((config) => config.channel_type === value);
                if (!form.getFieldValue('channel_config_id') && sameTypeConfigs.length === 1) {
                  form.setFieldValue('channel_config_id', sameTypeConfigs[0].channel_config_id);
                }
              }}
              options={[
                { label: 'Web', value: 'web' },
                { label: '微信', value: 'weixin' },
                { label: '飞书', value: 'feishu' },
                { label: '钉钉', value: 'dingtalk' },
                { label: '企微智能机器人', value: 'wecom_bot' },
                { label: 'QQ 机器人', value: 'qq' },
                { label: '企微自建应用', value: 'wechatcom_app' },
                { label: '公众号', value: 'wechatmp' },
                { label: '服务号', value: 'wechatmp_service' },
              ]}
              placeholder="选择渠道类型"
            />
          </Form.Item>
          <Form.Item
            name="channel_config_id"
            label="渠道配置"
            rules={[
              () => ({
                validator(_, value) {
                  const channelType = form.getFieldValue('channel_type');
                  if (TENANT_CHANNEL_TYPES.has(channelType) && !value) {
                    return Promise.reject(new Error('租户级渠道绑定必须选择渠道配置'));
                  }
                  return Promise.resolve();
                },
              }),
            ]}
          >
            <Select
              allowClear
              showSearch
              aria-label="渠道配置"
              options={channelConfigOptions}
              onChange={(value) => {
                const selected = channelConfigs.find((config) => config.channel_config_id === value);
                if (selected) {
                  form.setFieldValue('channel_type', selected.channel_type);
                }
              }}
              placeholder="选择租户自有渠道配置"
            />
          </Form.Item>
          <Form.Item name="agent_id" label="AI 员工" rules={[{ required: true }]}>
            <Select
              showSearch
              allowClear
              aria-label="AI 员工"
              options={tenantAgentOptions}
              placeholder="选择 AI 员工"
            />
          </Form.Item>
          <Form.Item name="enabled" label="启用" htmlFor="binding-enabled" valuePropName="checked">
            <Switch id="binding-enabled" aria-label="启用绑定" />
          </Form.Item>
        </Form>
      </Modal>
    </>
  );

  if (embedded) {
    return (
      <div className="channel-tab-panel">
        <div className="channel-tab-toolbar">{toolbar}</div>
        {content}
      </div>
    );
  }

  return (
    <ConsolePage
      title="渠道绑定管理"
      actions={toolbar}
    >
      {content}
    </ConsolePage>
  );
}
