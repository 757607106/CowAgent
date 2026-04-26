import { Alert, Button, Form, Input, InputNumber, Modal, Popconfirm, QRCode, Select, Space, Spin, Switch, Tag, Typography, message } from 'antd';
import { useEffect, useMemo, useRef, useState } from 'react';
import { PageTitle } from '../components/PageTitle';
import { DataTableShell } from '../components/console';
import { useRuntimeScope } from '../context/runtime';
import { api } from '../services/api';
import type { ChannelConfigItem, ChannelField, ChannelTypeItem, WeixinQrInfo } from '../types';

const WECOM_BOT_SDK_URL = 'https://wwcdn.weixin.qq.com/node/wework/js/wecom-aibot-sdk@0.1.0.min.js';
const WECOM_BOT_SOURCE = 'cowagent';

declare global {
  interface Window {
    WecomAIBotSDK?: {
      openBotInfoAuthWindow: (options: {
        source: string;
        onCreated?: (bot: { botid: string; secret: string }) => void;
        onError?: (error: { message?: string; code?: string }) => void;
      }) => void;
    };
  }
}

interface ChannelsPageProps {
  embedded?: boolean;
}

interface ChannelConfigFormValues {
  name: string;
  channel_type: string;
  enabled: boolean;
  config: Record<string, string | number | boolean>;
}

function channelTypeLabel(item: ChannelConfigItem, defs: ChannelTypeItem[]) {
  return item.label || defs.find((def) => def.channel_type === item.channel_type)?.label || item.channel_type;
}

function fieldInput(field: ChannelField, id: string) {
  if (field.type === 'secret') {
    return <Input.Password id={id} autoComplete="new-password" aria-label={field.label} />;
  }
  if (field.type === 'number') {
    return <InputNumber id={id} className="full-width-control" aria-label={field.label} />;
  }
  if (field.type === 'bool') {
    return <Switch id={id} aria-label={field.label} />;
  }
  if (field.type === 'list') {
    return <Input id={id} aria-label={field.label} />;
  }
  if (field.key === 'feishu_event_mode') {
    return (
      <Select
        id={id}
        aria-label={field.label}
        options={[
          { label: 'websocket', value: 'websocket' },
          { label: 'webhook', value: 'webhook' },
        ]}
      />
    );
  }
  return <Input id={id} aria-label={field.label} />;
}

function configValuesFromRow(row: ChannelConfigItem | null, typeDef?: ChannelTypeItem) {
  const config: Record<string, string | number | boolean> = {};
  typeDef?.fields.forEach((field) => {
    const value = row?.config?.[field.key] ?? field.default ?? (field.type === 'bool' ? false : '');
    config[field.key] = field.type === 'list' && Array.isArray(value) ? value.join(',') : value as string | number | boolean;
  });
  return config;
}

function renderQrStatus(info: WeixinQrInfo | null): string {
  if (!info?.qr_status) return '等待扫码';
  if (info.qr_status === 'confirmed') return '扫码成功，正在启动微信渠道';
  if (info.qr_status === 'scanned' || info.qr_status === 'scaned') return '已扫码，请在微信中确认';
  if (info.qr_status === 'expired') return '二维码已过期，已自动刷新';
  return '等待扫码';
}

async function ensureWecomSdkLoaded(): Promise<void> {
  if (window.WecomAIBotSDK) return;

  await new Promise<void>((resolve, reject) => {
    const existing = document.querySelector<HTMLScriptElement>(`script[src="${WECOM_BOT_SDK_URL}"]`);
    if (existing) {
      existing.addEventListener('load', () => resolve(), { once: true });
      existing.addEventListener('error', () => reject(new Error('企微授权 SDK 加载失败')), { once: true });
      return;
    }

    const script = document.createElement('script');
    script.src = WECOM_BOT_SDK_URL;
    script.async = true;
    script.onload = () => resolve();
    script.onerror = () => reject(new Error('企微授权 SDK 加载失败'));
    document.head.appendChild(script);
  });
}

export default function ChannelsPage({ embedded = false }: ChannelsPageProps) {
  const { tenantId, authUser } = useRuntimeScope();
  const canManage = authUser?.role === 'owner' || authUser?.role === 'admin';
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [open, setOpen] = useState(false);
  const [channelTypes, setChannelTypes] = useState<ChannelTypeItem[]>([]);
  const [configs, setConfigs] = useState<ChannelConfigItem[]>([]);
  const [editing, setEditing] = useState<ChannelConfigItem | null>(null);
  const [qrOpen, setQrOpen] = useState(false);
  const [qrConfig, setQrConfig] = useState<ChannelConfigItem | null>(null);
  const [qrInfo, setQrInfo] = useState<WeixinQrInfo | null>(null);
  const [qrLoading, setQrLoading] = useState(false);
  const [wecomAuthorizingId, setWecomAuthorizingId] = useState('');
  const qrTimerRef = useRef<number | null>(null);
  const [form] = Form.useForm<ChannelConfigFormValues>();
  const selectedType = Form.useWatch('channel_type', form);

  const typeOptions = useMemo(
    () => channelTypes.map((item) => ({ label: `${item.label} (${item.channel_type})`, value: item.channel_type })),
    [channelTypes],
  );
  const selectedTypeDef = channelTypes.find((item) => item.channel_type === selectedType);
  const qrValue = qrInfo?.qrcode_url || '';

  const load = async () => {
    setLoading(true);
    try {
      const data = await api.listChannelConfigs(tenantId);
      setChannelTypes(data.channel_types || []);
      setConfigs(data.channel_configs || []);
    } finally {
      setLoading(false);
    }
  };

  const clearQrTimer = () => {
    if (qrTimerRef.current) {
      window.clearTimeout(qrTimerRef.current);
      qrTimerRef.current = null;
    }
  };

  const pollWeixinQr = (channelConfigId: string) => {
    clearQrTimer();
    qrTimerRef.current = window.setTimeout(async () => {
      try {
        const data = await api.weixinQrPost('poll', channelConfigId);
        setQrInfo(data);
        if (data.qr_status === 'confirmed') {
          message.success('微信扫码确认成功');
          clearQrTimer();
          await load();
          return;
        }
        pollWeixinQr(channelConfigId);
      } catch {
        pollWeixinQr(channelConfigId);
      }
    }, 2000);
  };

  const openWeixinQr = async (row: ChannelConfigItem) => {
    clearQrTimer();
    setQrConfig(row);
    setQrInfo(null);
    setQrOpen(true);
    setQrLoading(true);
    try {
      const data = await api.weixinQrGet(row.channel_config_id);
      setQrInfo(data);
      pollWeixinQr(row.channel_config_id);
    } catch (error) {
      message.error(error instanceof Error ? error.message : '获取微信二维码失败');
    } finally {
      setQrLoading(false);
    }
  };

  const refreshWeixinQr = async () => {
    if (!qrConfig) return;
    clearQrTimer();
    setQrLoading(true);
    try {
      const data = await api.weixinQrPost('refresh', qrConfig.channel_config_id);
      setQrInfo(data);
      pollWeixinQr(qrConfig.channel_config_id);
    } catch (error) {
      message.error(error instanceof Error ? error.message : '刷新微信二维码失败');
    } finally {
      setQrLoading(false);
    }
  };

  const openCreate = () => {
    const firstType = channelTypes[0]?.channel_type || 'feishu';
    const typeDef = channelTypes.find((item) => item.channel_type === firstType);
    setEditing(null);
    form.setFieldsValue({
      name: '',
      channel_type: firstType,
      enabled: true,
      config: configValuesFromRow(null, typeDef),
    });
    setOpen(true);
  };

  const openEdit = (row: ChannelConfigItem) => {
    const typeDef = channelTypes.find((item) => item.channel_type === row.channel_type);
    setEditing(row);
    form.setFieldsValue({
      name: row.name,
      channel_type: row.channel_type,
      enabled: row.enabled,
      config: configValuesFromRow(row, typeDef),
    });
    setOpen(true);
  };

  const submit = async () => {
    const values = await form.validateFields();
    setSubmitting(true);
    try {
      const payload = {
        tenant_id: tenantId,
        name: values.name,
        channel_type: values.channel_type,
        enabled: values.enabled ?? true,
        config: values.config || {},
      };
      if (editing) {
        await api.updateChannelConfig(editing.channel_config_id, payload);
        message.success('渠道配置已更新');
      } else {
        const response = await api.createChannelConfig(payload) as { channel_config?: ChannelConfigItem };
        message.success('渠道配置已创建');
        if (response.channel_config?.channel_type === 'weixin') {
          setOpen(false);
          await load();
          await openWeixinQr(response.channel_config);
          return;
        }
      }
      setOpen(false);
      await load();
    } finally {
      setSubmitting(false);
    }
  };

  const remove = async (row: ChannelConfigItem) => {
    await api.deleteChannelConfig(row.tenant_id, row.channel_config_id);
    message.success('渠道配置已删除');
    await load();
  };

  const startWecomBotAuth = async (row: ChannelConfigItem) => {
    setWecomAuthorizingId(row.channel_config_id);
    try {
      await ensureWecomSdkLoaded();
      if (!window.WecomAIBotSDK) {
        throw new Error('企微授权 SDK 不可用');
      }
      window.WecomAIBotSDK.openBotInfoAuthWindow({
        source: WECOM_BOT_SOURCE,
        onCreated: async (bot) => {
          try {
            await api.updateChannelConfig(row.channel_config_id, {
              tenant_id: tenantId,
              enabled: true,
              config: {
                wecom_bot_id: bot.botid,
                wecom_bot_secret: bot.secret,
              },
            });
            message.success('企微机器人授权成功');
            await load();
          } catch (error) {
            message.error(error instanceof Error ? error.message : '保存企微授权失败');
          } finally {
            setWecomAuthorizingId('');
          }
        },
        onError: (error) => {
          setWecomAuthorizingId('');
          message.error(error.message || error.code || '企微授权失败');
        },
      });
    } catch (error) {
      setWecomAuthorizingId('');
      message.error(error instanceof Error ? error.message : '企微授权失败');
    }
  };

  useEffect(() => {
    void load();
    return () => clearQrTimer();
  }, [tenantId]);

  const content = (
    <>
      {!embedded ? (
        <PageTitle
          title="渠道配置"
          description="维护本租户自己的飞书、公众号、QQ 等渠道接入密钥。"
          extra={(
            <Space>
              <Button onClick={() => void load()}>刷新</Button>
              {canManage && <Button type="primary" onClick={openCreate}>新增渠道配置</Button>}
            </Space>
          )}
        />
      ) : (
        <div className="channel-tab-toolbar">
          <Space>
            <Button onClick={() => void load()}>刷新</Button>
            {canManage && <Button type="primary" onClick={openCreate}>新增渠道配置</Button>}
          </Space>
        </div>
      )}

      <DataTableShell<ChannelConfigItem>
        compact={embedded}
        className="channel-table-shell"
        title={embedded ? undefined : '渠道列表'}
        rowKey="channel_config_id"
        loading={loading}
        dataSource={configs}
        pagination={{
          pageSize: embedded ? 10 : 12,
          hideOnSinglePage: configs.length <= (embedded ? 10 : 12),
        }}
        tableLayout="fixed"
        columns={[
          {
            title: '名称',
            dataIndex: 'name',
            width: '15%',
            ellipsis: true,
            render: (value: string) => (
              <span className="entity-title-cell">
                <span className="entity-title-cell-main">{value}</span>
              </span>
            ),
          },
          {
            title: '渠道',
            dataIndex: 'channel_type',
            width: '12%',
            render: (_value: string, row) => <Tag color="blue">{channelTypeLabel(row, channelTypes)}</Tag>,
          },
          {
            title: '状态',
            dataIndex: 'enabled',
            width: '8%',
            render: (value: boolean) => (value ? <Tag color="green">启用</Tag> : <Tag>停用</Tag>),
          },
          {
            title: '回调路径',
            dataIndex: 'webhook_path',
            width: '17%',
            render: (value: string, row) => {
              if (row.channel_type === 'weixin') return <Typography.Text type="secondary">扫码登录</Typography.Text>;
              return value ? (
                <Typography.Text className="channel-webhook-text" copyable code ellipsis={{ tooltip: value }}>
                  {value}
                </Typography.Text>
              ) : (
                <Typography.Text type="secondary">长连接</Typography.Text>
              );
            },
          },
          {
            title: '密钥',
            width: '22%',
            render: (_, row) => {
              const secretFields = (row.fields || []).filter((field) => field.type === 'secret');
              if (!secretFields.length) return <Typography.Text type="secondary">无</Typography.Text>;
              return (
                <Space wrap size={0} className="channel-secret-tags">
                  {secretFields.map((field) => (
                    <Tag key={field.key} color={field.secret_set ? 'green' : 'default'}>
                      {field.label}{field.secret_set ? ' 已设置' : ' 未设置'}
                    </Tag>
                  ))}
                </Space>
              );
            },
          },
          {
            title: '操作',
            width: '26%',
            align: 'right',
            render: (_, row) => canManage ? (
              <Space wrap size={0} className="channel-row-actions">
                {row.channel_type === 'weixin' && (
                  <Button size="small" type="primary" onClick={() => void openWeixinQr(row)}>扫码登录</Button>
                )}
                {row.channel_type === 'wecom_bot' && (
                  <Button
                    size="small"
                    type="primary"
                    loading={wecomAuthorizingId === row.channel_config_id}
                    onClick={() => void startWecomBotAuth(row)}
                  >
                    扫码授权
                  </Button>
                )}
                <Button size="small" onClick={() => openEdit(row)}>编辑</Button>
                <Popconfirm title="确认删除该渠道配置？相关绑定将无法继续路由。" onConfirm={() => void remove(row)}>
                  <Button size="small" danger>删除</Button>
                </Popconfirm>
              </Space>
            ) : null,
          },
        ]}
      />

      <Modal
        open={open}
        title={editing ? '编辑渠道配置' : '新增渠道配置'}
        onCancel={() => setOpen(false)}
        onOk={() => void submit()}
        confirmLoading={submitting}
        destroyOnClose
        width="min(45rem, calc(100vw - 3rem))"
      >
        <Form form={form} layout="vertical">
          <Form.Item name="name" label="名称" rules={[{ required: true, message: '请输入名称' }]}>
            <Input aria-label="名称" />
          </Form.Item>
          <Form.Item name="channel_type" label="渠道类型" rules={[{ required: true, message: '请选择渠道类型' }]}>
            <Select
              showSearch
              aria-label="渠道类型"
              options={typeOptions}
              disabled={Boolean(editing)}
              onChange={(value) => {
                const typeDef = channelTypes.find((item) => item.channel_type === value);
                form.setFieldValue('config', configValuesFromRow(null, typeDef));
              }}
            />
          </Form.Item>
          {selectedTypeDef?.fields.map((field) => (
            <Form.Item
              key={field.key}
              name={['config', field.key]}
              label={field.type === 'secret' && editing ? `${field.label}（留空或保留掩码则不覆盖）` : field.label}
              htmlFor={`channel-field-${field.key}`}
              valuePropName={field.type === 'bool' ? 'checked' : 'value'}
            >
              {fieldInput(field, `channel-field-${field.key}`)}
            </Form.Item>
          ))}
          <Form.Item name="enabled" label="启用" htmlFor="channel-enabled" valuePropName="checked">
            <Switch id="channel-enabled" aria-label="启用渠道配置" />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        open={qrOpen}
        title={qrConfig ? `${qrConfig.name} - 微信扫码登录` : '微信扫码登录'}
        onCancel={() => {
          setQrOpen(false);
          clearQrTimer();
        }}
        footer={(
          <Space>
            <Button onClick={() => {
              setQrOpen(false);
              clearQrTimer();
            }}>关闭</Button>
            <Button onClick={() => void refreshWeixinQr()} loading={qrLoading}>刷新二维码</Button>
          </Space>
        )}
        width="min(32.5rem, calc(100vw - 3rem))"
      >
        <Space vertical size={16} className="full-width-stack">
          <Alert
            type="info"
            showIcon
            title="使用微信扫码确认"
            description="扫码成功后，Bot Token 会写入当前租户的渠道配置，并自动启动该微信渠道。"
          />
          <div className="channel-qr-box channel-qr-box-large">
            {qrLoading ? (
              <Spin />
            ) : qrValue ? (
              <QRCode value={qrValue} size={240} />
            ) : qrInfo?.qr_image ? (
              <img src={qrInfo.qr_image} alt="weixin-qr" />
            ) : null}
          </div>
          <Space vertical size={4}>
            <Typography.Text strong>{renderQrStatus(qrInfo)}</Typography.Text>
            <Typography.Text type="secondary">
              {qrInfo?.message || '保持弹窗打开，确认后系统会自动更新渠道配置。'}
            </Typography.Text>
            {qrValue ? (
              <Typography.Text type="secondary" copyable={{ text: qrValue }}>
                二维码链接
              </Typography.Text>
            ) : null}
          </Space>
        </Space>
      </Modal>
    </>
  );

  return (
    <div className={embedded ? 'channels-page-embedded channel-tab-panel' : 'channels-page'}>
      {content}
    </div>
  );
}
