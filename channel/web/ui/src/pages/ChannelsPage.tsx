import {
  Alert,
  Avatar,
  Button,
  Card,
  Col,
  Empty,
  Input,
  Popconfirm,
  Row,
  Select,
  Space,
  Spin,
  Statistic,
  Switch,
  Tag,
  Typography,
  message,
} from 'antd';
import {
  DisconnectOutlined,
  LinkOutlined,
  LockOutlined,
  PlusOutlined,
  QrcodeOutlined,
  ReloadOutlined,
  RobotOutlined,
  SafetyCertificateOutlined,
  SyncOutlined,
  ThunderboltOutlined,
  WechatOutlined,
} from '@ant-design/icons';
import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import { PageTitle } from '../components/PageTitle';
import { api } from '../services/api';
import type { ChannelField, ChannelItem, WeixinQrInfo } from '../types';

const WECOM_BOT_SDK_URL = 'https://wwcdn.weixin.qq.com/node/wework/js/wecom-aibot-sdk@0.1.0.min.js';
const WECOM_BOT_SOURCE = 'cowagent';

type ChannelDraft = Record<string, string | number | boolean>;
type SecretTouchedMap = Record<string, boolean>;
type WecomAuthState = {
  status: 'idle' | 'pending' | 'success' | 'error';
  text?: string;
};

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

function getChannelLabel(channel: Pick<ChannelItem, 'name' | 'label'>): string {
  return channel.label?.zh || channel.label?.en || channel.name;
}

function isMaskedSecret(value: unknown): boolean {
  return typeof value === 'string' && value.includes('*');
}

function getInitialDraft(channel: ChannelItem): ChannelDraft {
  const next: ChannelDraft = {};
  channel.fields.forEach((field) => {
    next[field.key] = field.value ?? field.default ?? (field.type === 'bool' ? false : '');
  });
  return next;
}

function getInitialSecretTouched(channel: ChannelItem): SecretTouchedMap {
  const next: SecretTouchedMap = {};
  channel.fields.forEach((field) => {
    if (field.type === 'secret') {
      next[field.key] = !isMaskedSecret(field.value);
    }
  });
  return next;
}

function getStatusMeta(channel: ChannelItem): { color: string; text: string; tone: 'success' | 'processing' | 'warning' } {
  if (!channel.active) {
    return { color: 'default', text: '未接入', tone: 'warning' };
  }

  if (channel.name === 'weixin') {
    if (channel.login_status === 'logged_in') {
      return { color: 'green', text: '已连接', tone: 'success' };
    }
    if (channel.login_status === 'scanned' || channel.login_status === 'scaned') {
      return { color: 'gold', text: '已扫码待确认', tone: 'processing' };
    }
    return { color: 'gold', text: '等待扫码恢复登录', tone: 'processing' };
  }

  if (channel.name === 'wecom_bot' && !wecomBotHasCreds(channel)) {
    return { color: 'gold', text: '等待授权完成', tone: 'processing' };
  }

  return { color: 'green', text: '已连接', tone: 'success' };
}

function getChannelAvatar(channel: ChannelItem) {
  const styleMap: Record<string, { bg: string; color: string; icon: ReactNode }> = {
    weixin: { bg: '#e8fff0', color: '#11a75c', icon: <WechatOutlined /> },
    wecom_bot: { bg: '#eef8ef', color: '#1d8f61', icon: <RobotOutlined /> },
    feishu: { bg: '#edf5ff', color: '#1677ff', icon: <LinkOutlined /> },
    dingtalk: { bg: '#edf6ff', color: '#2f6bff', icon: <SafetyCertificateOutlined /> },
    qq: { bg: '#eef4ff', color: '#4258ff', icon: <ThunderboltOutlined /> },
    wechatcom_app: { bg: '#eefbf5', color: '#2c8f60', icon: <SafetyCertificateOutlined /> },
    wechatmp: { bg: '#eefbf3', color: '#17a35b', icon: <WechatOutlined /> },
  };
  const current = styleMap[channel.name] || { bg: '#f2f4f8', color: '#45526a', icon: <LinkOutlined /> };
  return (
    <Avatar style={{ background: current.bg, color: current.color }} icon={current.icon} />
  );
}

function wecomBotHasCreds(channel: ChannelItem): boolean {
  const botId = channel.fields.find((field) => field.key === 'wecom_bot_id')?.value;
  const secret = channel.fields.find((field) => field.key === 'wecom_bot_secret')?.value;
  return Boolean(botId && secret);
}

function buildPayloadFromDraft(
  channel: ChannelItem,
  draft: ChannelDraft,
  secretTouched: SecretTouchedMap,
): Record<string, string | number | boolean> {
  const next: Record<string, string | number | boolean> = {};

  channel.fields.forEach((field) => {
    const rawValue = draft[field.key];
    if (field.type === 'secret' && !secretTouched[field.key] && isMaskedSecret(rawValue)) {
      return;
    }

    if (field.type === 'bool') {
      next[field.key] = Boolean(rawValue);
      return;
    }

    if (field.type === 'number') {
      const normalized = rawValue === '' || rawValue === undefined || rawValue === null
        ? field.default
        : rawValue;
      if (normalized === '' || normalized === undefined || normalized === null) {
        return;
      }
      next[field.key] = Number(normalized);
      return;
    }

    if (rawValue === undefined || rawValue === null) {
      return;
    }

    next[field.key] = String(rawValue);
  });

  return next;
}

async function ensureWecomSdkLoaded(): Promise<void> {
  if (window.WecomAIBotSDK) {
    return;
  }

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

function renderQrStatus(info: WeixinQrInfo | null): string {
  if (!info?.qr_status) return '等待扫码';
  if (info.qr_status === 'confirmed') return '扫码成功，正在接入';
  if (info.qr_status === 'scanned' || info.qr_status === 'scaned') return '已扫码，请在微信中确认';
  if (info.qr_status === 'expired') return '二维码已过期，已自动刷新';
  return '等待扫码';
}

export default function ChannelsPage() {
  const [channels, setChannels] = useState<ChannelItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [drafts, setDrafts] = useState<Record<string, ChannelDraft>>({});
  const [secretTouchedMap, setSecretTouchedMap] = useState<Record<string, SecretTouchedMap>>({});
  const [savingChannel, setSavingChannel] = useState('');
  const [disconnectingChannel, setDisconnectingChannel] = useState('');
  const [connectingChannel, setConnectingChannel] = useState('');
  const [selectedChannelName, setSelectedChannelName] = useState('');
  const [weixinMode, setWeixinMode] = useState<'connect' | 'active' | null>(null);
  const [weixinInfo, setWeixinInfo] = useState<WeixinQrInfo | null>(null);
  const [weixinLoading, setWeixinLoading] = useState(false);
  const [wecomMode, setWecomMode] = useState<'scan' | 'manual'>('scan');
  const [wecomAuth, setWecomAuth] = useState<WecomAuthState>({ status: 'idle' });

  const weixinQrTimerRef = useRef<number | null>(null);
  const weixinStatusTimerRef = useRef<number | null>(null);
  const mountedRef = useRef(true);

  const syncChannelStates = (nextChannels: ChannelItem[], resetDrafts = false) => {
    setChannels(nextChannels);
    setDrafts((prev) => {
      const next: Record<string, ChannelDraft> = {};
      nextChannels.forEach((channel) => {
        const initial = getInitialDraft(channel);
        next[channel.name] = resetDrafts || !prev[channel.name]
          ? initial
          : { ...initial, ...prev[channel.name] };
      });
      return next;
    });
    setSecretTouchedMap((prev) => {
      const next: Record<string, SecretTouchedMap> = {};
      nextChannels.forEach((channel) => {
        const initial = getInitialSecretTouched(channel);
        next[channel.name] = resetDrafts || !prev[channel.name]
          ? initial
          : { ...initial, ...prev[channel.name] };
      });
      return next;
    });
  };

  const clearWeixinTimers = () => {
    if (weixinQrTimerRef.current) {
      window.clearTimeout(weixinQrTimerRef.current);
      weixinQrTimerRef.current = null;
    }
    if (weixinStatusTimerRef.current) {
      window.clearTimeout(weixinStatusTimerRef.current);
      weixinStatusTimerRef.current = null;
    }
  };

  const loadChannels = async ({ resetDrafts = false, silent = false }: { resetDrafts?: boolean; silent?: boolean } = {}) => {
    if (!silent) {
      setLoading(true);
    }
    try {
      const data = await api.listChannels();
      if (!mountedRef.current) return;
      syncChannelStates(data.channels || [], resetDrafts);
    } finally {
      if (!silent && mountedRef.current) {
        setLoading(false);
      }
    }
  };

  const pollActiveWeixinStatus = () => {
    clearWeixinTimers();
    weixinStatusTimerRef.current = window.setTimeout(async () => {
      try {
        const data = await api.listChannels();
        if (!mountedRef.current) return;
        const list = data.channels || [];
        syncChannelStates(list, false);
        const weixinChannel = list.find((channel) => channel.name === 'weixin');
        if (!weixinChannel || !weixinChannel.active) {
          setWeixinInfo(null);
          setWeixinMode(null);
          return;
        }
        if (weixinChannel.login_status === 'logged_in') {
          setWeixinInfo((prev) => (prev ? { ...prev, qr_status: 'confirmed' } : prev));
          message.success('微信通道已恢复登录');
          return;
        }
        setWeixinInfo((prev) => ({ ...(prev || { status: 'success' }), qr_status: weixinChannel.login_status }));
        pollActiveWeixinStatus();
      } catch {
        if (mountedRef.current) {
          pollActiveWeixinStatus();
        }
      }
    }, 3000);
  };

  const pollWeixinQrSession = () => {
    clearWeixinTimers();
    weixinQrTimerRef.current = window.setTimeout(async () => {
      try {
        const data = await api.weixinQrPost('poll');
        if (!mountedRef.current) return;
        setWeixinInfo(data);

        if (data.qr_status === 'confirmed') {
          message.success('微信扫码确认成功，正在接入渠道');
          setConnectingChannel('weixin');
          await api.channelAction({ action: 'connect', channel: 'weixin', config: {} });
          await loadChannels({ resetDrafts: true, silent: true });
          setConnectingChannel('');
          setSelectedChannelName('');
          setWeixinMode(null);
          return;
        }

        pollWeixinQrSession();
      } catch {
        if (mountedRef.current) {
          pollWeixinQrSession();
        }
      }
    }, 2000);
  };

  const startWeixinQrLogin = async (mode: 'connect' | 'active') => {
    clearWeixinTimers();
    setWeixinMode(mode);
    setWeixinLoading(true);
    try {
      const data = await api.weixinQrGet();
      if (!mountedRef.current) return;
      setWeixinInfo(data);
      if (mode === 'active' || data.source === 'channel') {
        pollActiveWeixinStatus();
      } else {
        pollWeixinQrSession();
      }
    } catch (error) {
      message.error(error instanceof Error ? error.message : '获取微信二维码失败');
    } finally {
      if (mountedRef.current) {
        setWeixinLoading(false);
      }
    }
  };

  const connectWecomByAuth = async (botId: string, secret: string) => {
    setConnectingChannel('wecom_bot');
    try {
      await api.channelAction({
        action: 'connect',
        channel: 'wecom_bot',
        config: {
          wecom_bot_id: botId,
          wecom_bot_secret: secret,
        },
      });
      setWecomAuth({ status: 'success', text: '企微机器人授权成功，渠道正在接入。' });
      await loadChannels({ resetDrafts: true, silent: true });
      setSelectedChannelName('');
    } catch (error) {
      setWecomAuth({ status: 'error', text: error instanceof Error ? error.message : '企微授权失败' });
    } finally {
      if (mountedRef.current) {
        setConnectingChannel('');
      }
    }
  };

  const startWecomBotAuth = async () => {
    setWecomAuth({ status: 'pending', text: '正在打开企微授权窗口...' });
    try {
      await ensureWecomSdkLoaded();
      if (!window.WecomAIBotSDK) {
        throw new Error('企微授权 SDK 不可用');
      }
      window.WecomAIBotSDK.openBotInfoAuthWindow({
        source: WECOM_BOT_SOURCE,
        onCreated: (bot) => {
          void connectWecomByAuth(bot.botid, bot.secret);
        },
        onError: (error) => {
          setWecomAuth({
            status: 'error',
            text: error.message || error.code || '企微授权失败',
          });
        },
      });
    } catch (error) {
      setWecomAuth({ status: 'error', text: error instanceof Error ? error.message : '企微授权失败' });
    }
  };

  const updateDraftValue = (channelName: string, field: ChannelField, value: string | number | boolean) => {
    setDrafts((prev) => ({
      ...prev,
      [channelName]: {
        ...(prev[channelName] || {}),
        [field.key]: value,
      },
    }));

    if (field.type === 'secret') {
      setSecretTouchedMap((prev) => ({
        ...prev,
        [channelName]: {
          ...(prev[channelName] || {}),
          [field.key]: true,
        },
      }));
    }
  };

  const handleSecretFocus = (channelName: string, field: ChannelField) => {
    const currentValue = drafts[channelName]?.[field.key];
    if (!isMaskedSecret(currentValue)) {
      return;
    }
    updateDraftValue(channelName, field, '');
  };

  const saveChannelConfig = async (channel: ChannelItem) => {
    setSavingChannel(channel.name);
    try {
      const config = buildPayloadFromDraft(channel, drafts[channel.name] || {}, secretTouchedMap[channel.name] || {});
      await api.channelAction({ action: 'save', channel: channel.name, config });
      message.success(channel.active ? '渠道配置已保存' : '配置已更新');
      await loadChannels({ resetDrafts: true, silent: true });
    } catch (error) {
      message.error(error instanceof Error ? error.message : '保存渠道配置失败');
    } finally {
      if (mountedRef.current) {
        setSavingChannel('');
      }
    }
  };

  const connectSelectedChannel = async () => {
    if (!selectedChannelName) {
      return;
    }

    const target = channels.find((channel) => channel.name === selectedChannelName);
    if (!target) {
      return;
    }

    if (target.name === 'weixin') {
      await startWeixinQrLogin('connect');
      return;
    }

    if (target.name === 'wecom_bot' && wecomMode === 'scan') {
      await startWecomBotAuth();
      return;
    }

    setConnectingChannel(target.name);
    try {
      const config = buildPayloadFromDraft(target, drafts[target.name] || {}, secretTouchedMap[target.name] || {});
      await api.channelAction({ action: 'connect', channel: target.name, config });
      message.success(`${getChannelLabel(target)} 渠道接入请求已提交`);
      setSelectedChannelName('');
      setWeixinInfo(null);
      setWeixinMode(null);
      setWecomAuth({ status: 'idle' });
      await loadChannels({ resetDrafts: true, silent: true });
    } catch (error) {
      message.error(error instanceof Error ? error.message : '接入渠道失败');
    } finally {
      if (mountedRef.current) {
        setConnectingChannel('');
      }
    }
  };

  const disconnectChannel = async (channel: ChannelItem) => {
    setDisconnectingChannel(channel.name);
    try {
      await api.channelAction({ action: 'disconnect', channel: channel.name });
      message.success(`${getChannelLabel(channel)} 已断开`);
      if (channel.name === 'weixin') {
        setWeixinInfo(null);
        setWeixinMode(null);
        clearWeixinTimers();
      }
      await loadChannels({ resetDrafts: true, silent: true });
    } catch (error) {
      message.error(error instanceof Error ? error.message : '断开渠道失败');
    } finally {
      if (mountedRef.current) {
        setDisconnectingChannel('');
      }
    }
  };

  useEffect(() => {
    mountedRef.current = true;
    void loadChannels({ resetDrafts: true });
    return () => {
      mountedRef.current = false;
      clearWeixinTimers();
    };
  }, []);

  useEffect(() => {
    const channel = channels.find((item) => item.name === selectedChannelName);
    if (!channel) {
      setWeixinInfo(null);
      setWeixinMode(null);
      setWecomAuth({ status: 'idle' });
      clearWeixinTimers();
      return;
    }

    if (channel.name === 'wecom_bot') {
      setWecomMode(wecomBotHasCreds(channel) ? 'manual' : 'scan');
      setWecomAuth({ status: 'idle' });
      clearWeixinTimers();
      setWeixinInfo(null);
      setWeixinMode(null);
      return;
    }

    if (channel.name === 'weixin') {
      void startWeixinQrLogin('connect');
      setWecomAuth({ status: 'idle' });
      return;
    }

    clearWeixinTimers();
    setWeixinInfo(null);
    setWeixinMode(null);
    setWecomAuth({ status: 'idle' });
  }, [selectedChannelName]);

  const activeChannels = useMemo(() => channels.filter((channel) => channel.active), [channels]);
  const availableChannels = useMemo(() => channels.filter((channel) => !channel.active), [channels]);
  const waitingCount = useMemo(
    () => activeChannels.filter((channel) => getStatusMeta(channel).tone !== 'success').length,
    [activeChannels],
  );
  const selectedChannel = channels.find((channel) => channel.name === selectedChannelName) || null;
  const pageBootstrapping = loading && channels.length === 0;

  const renderField = (channel: ChannelItem, field: ChannelField) => {
    const channelName = channel.name;
    const value = drafts[channelName]?.[field.key] ?? '';

    if (field.type === 'bool') {
      return (
        <div key={field.key} className="channel-field channel-field-switch">
          <div>
            <Typography.Text strong>{field.label}</Typography.Text>
            <div className="channel-field-hint">开关配置会在保存或接入时生效。</div>
          </div>
          <Switch
            checked={Boolean(value)}
            onChange={(checked) => updateDraftValue(channelName, field, checked)}
          />
        </div>
      );
    }

    return (
      <div key={field.key} className="channel-field">
        <Typography.Text strong>{field.label}</Typography.Text>
        <Input
          value={String(value ?? '')}
          type={field.type === 'number' ? 'number' : 'text'}
          placeholder={field.label}
          onFocus={() => {
            if (field.type === 'secret') {
              handleSecretFocus(channelName, field);
            }
          }}
          onChange={(event) => updateDraftValue(channelName, field, event.target.value)}
          prefix={field.type === 'secret' ? <LockOutlined /> : undefined}
        />
      </div>
    );
  };

  return (
    <div className="channels-page">
      <PageTitle
        title="渠道管理"
        description="按旧版能力补齐渠道接入、二维码授权和运行状态查看。"
        extra={(
          <Space>
            <Button icon={<ReloadOutlined />} onClick={() => void loadChannels({ resetDrafts: true })}>
              刷新渠道
            </Button>
          </Space>
        )}
      />

      <div className="console-summary-grid">
        <Card>
          <Statistic title="已接入渠道" value={pageBootstrapping ? '--' : activeChannels.length} prefix={<LinkOutlined />} />
        </Card>
        <Card>
          <Statistic title="可新增渠道" value={pageBootstrapping ? '--' : availableChannels.length} prefix={<PlusOutlined />} />
        </Card>
        <Card>
          <Statistic
            title="待完成授权"
            value={pageBootstrapping ? '--' : waitingCount}
            prefix={<SyncOutlined spin={waitingCount > 0} />}
          />
        </Card>
      </div>

      <Row gutter={[16, 16]}>
        <Col xs={24} xl={15}>
          <Card
            loading={pageBootstrapping}
            title="已接入渠道"
            extra={<Tag color={activeChannels.length ? 'green' : 'default'}>{activeChannels.length} 个在线渠道</Tag>}
          >
            {activeChannels.length === 0 ? (
              <Empty
                image={Empty.PRESENTED_IMAGE_SIMPLE}
                description="当前还没有接入任何外部渠道。"
              />
            ) : (
              <Space direction="vertical" size={16} style={{ width: '100%' }}>
                {activeChannels.map((channel) => {
                  const status = getStatusMeta(channel);
                  const needsWeixinQr = channel.name === 'weixin' && channel.login_status !== 'logged_in';
                  const needsWecomAuth = channel.name === 'wecom_bot' && !wecomBotHasCreds(channel);

                  return (
                    <Card key={channel.name} className="channel-card">
                      <div className="channel-card-header">
                        <Space align="start" size={12}>
                          {getChannelAvatar(channel)}
                          <div>
                            <Typography.Title level={5} style={{ margin: 0 }}>
                              {getChannelLabel(channel)}
                            </Typography.Title>
                            <Typography.Text type="secondary" style={{ fontFamily: 'monospace' }}>
                              {channel.name}
                            </Typography.Text>
                          </div>
                        </Space>
                        <Space wrap>
                          <Tag color={status.color}>{status.text}</Tag>
                          <Popconfirm
                            title={`确认断开 ${getChannelLabel(channel)} 吗？`}
                            onConfirm={() => void disconnectChannel(channel)}
                          >
                            <Button
                              danger
                              icon={<DisconnectOutlined />}
                              loading={disconnectingChannel === channel.name}
                            >
                              断开
                            </Button>
                          </Popconfirm>
                        </Space>
                      </div>

                      {needsWeixinQr ? (
                        <Alert
                          type="warning"
                          showIcon
                          message="微信通道已存在，但当前登录态未完成。"
                          description="重新打开扫码面板后，扫描二维码即可恢复在线。"
                          action={(
                            <Button size="small" icon={<QrcodeOutlined />} onClick={() => void startWeixinQrLogin('active')}>
                              打开扫码面板
                            </Button>
                          )}
                          style={{ marginBottom: 16 }}
                        />
                      ) : null}

                      {needsWecomAuth ? (
                        <Alert
                          type="info"
                          showIcon
                          message="企微机器人还未完成授权"
                          description="可以重新发起扫码授权，也可以在下方直接补齐 Bot ID / Secret。"
                          action={(
                            <Button size="small" icon={<RobotOutlined />} onClick={() => void startWecomBotAuth()}>
                              重新授权
                            </Button>
                          )}
                          style={{ marginBottom: 16 }}
                        />
                      ) : null}

                      {weixinMode === 'active' && weixinInfo && channel.name === 'weixin' ? (
                        <div className="channel-qr-panel">
                          <div>
                            <Typography.Text strong>微信扫码登录</Typography.Text>
                            <div className="channel-field-hint">{renderQrStatus(weixinInfo)}</div>
                          </div>
                          <div className="channel-qr-box">
                            {weixinLoading ? <Spin /> : weixinInfo.qr_image ? <img src={weixinInfo.qr_image} alt="weixin-qr" /> : null}
                          </div>
                          <Space>
                            <Button icon={<ReloadOutlined />} onClick={() => void startWeixinQrLogin('active')}>
                              刷新二维码
                            </Button>
                            <Typography.Text type="secondary">
                              {weixinInfo.qr_status === 'confirmed' ? '登录恢复成功' : '使用微信扫码后将自动轮询状态'}
                            </Typography.Text>
                          </Space>
                        </div>
                      ) : null}

                      {channel.fields.length > 0 ? (
                        <>
                          <div className="channel-form-grid">
                            {channel.fields.map((field) => renderField(channel, field))}
                          </div>
                          <div className="channel-card-actions">
                            <Typography.Text type="secondary">
                              密钥字段保持掩码时不会覆盖原值。
                            </Typography.Text>
                            <Button
                              type="primary"
                              loading={savingChannel === channel.name}
                              onClick={() => void saveChannelConfig(channel)}
                            >
                              保存配置
                            </Button>
                          </div>
                        </>
                      ) : (
                        <Typography.Text type="secondary">
                          当前渠道没有额外配置项，可直接通过扫码或登录状态维持在线。
                        </Typography.Text>
                      )}
                    </Card>
                  );
                })}
              </Space>
            )}
          </Card>
        </Col>

        <Col xs={24} xl={9}>
          <Card
            loading={pageBootstrapping}
            title="新增接入"
            extra={availableChannels.length > 0 ? <Tag color="blue">{availableChannels.length} 个可接入</Tag> : null}
          >
            {availableChannels.length === 0 ? (
              <Alert
                type="success"
                showIcon
                message="所有渠道都已接入"
                description="如果需要重新配置，请在左侧已接入渠道卡片中操作。"
              />
            ) : (
              <Space direction="vertical" size={16} style={{ width: '100%' }}>
                <div className="channel-field">
                  <Typography.Text strong>选择要接入的渠道</Typography.Text>
                  <Select
                    placeholder="请选择渠道"
                    value={selectedChannelName || undefined}
                    onChange={setSelectedChannelName}
                    options={availableChannels.map((channel) => ({
                      label: `${getChannelLabel(channel)} (${channel.name})`,
                      value: channel.name,
                    }))}
                  />
                </div>

                {!selectedChannel ? (
                  <Empty
                    image={Empty.PRESENTED_IMAGE_SIMPLE}
                    description="选择一个未接入渠道后即可开始配置或扫码授权。"
                  />
                ) : (
                  <div className="channel-onboarding-panel">
                    <div className="channel-onboarding-head">
                      <Space size={12}>
                        {getChannelAvatar(selectedChannel)}
                        <div>
                          <Typography.Title level={5} style={{ margin: 0 }}>
                            {getChannelLabel(selectedChannel)}
                          </Typography.Title>
                          <Typography.Text type="secondary">{selectedChannel.name}</Typography.Text>
                        </div>
                      </Space>
                    </div>

                    {selectedChannel.name === 'weixin' ? (
                      <div className="channel-qr-panel">
                        <Alert
                          type="info"
                          showIcon
                          message="微信接入需要扫码确认"
                          description="二维码会自动刷新并轮询确认状态，扫码成功后会自动发起接入。"
                        />
                        <div className="channel-qr-box channel-qr-box-large">
                          {weixinLoading ? <Spin /> : weixinInfo?.qr_image ? <img src={weixinInfo.qr_image} alt="weixin-qr" /> : null}
                        </div>
                        <Space direction="vertical" size={6} style={{ width: '100%' }}>
                          <Typography.Text strong>{renderQrStatus(weixinInfo)}</Typography.Text>
                          <Typography.Text type="secondary">
                            {weixinInfo?.message || '保持当前页面打开，确认后会自动接入微信通道。'}
                          </Typography.Text>
                        </Space>
                        <Button icon={<ReloadOutlined />} onClick={() => void startWeixinQrLogin('connect')}>
                          刷新二维码
                        </Button>
                      </div>
                    ) : null}

                    {selectedChannel.name === 'wecom_bot' ? (
                      <Space direction="vertical" size={16} style={{ width: '100%' }}>
                        <div className="channel-mode-switch">
                          <Button
                            type={wecomMode === 'scan' ? 'primary' : 'default'}
                            icon={<QrcodeOutlined />}
                            onClick={() => setWecomMode('scan')}
                          >
                            扫码授权
                          </Button>
                          <Button
                            type={wecomMode === 'manual' ? 'primary' : 'default'}
                            icon={<LockOutlined />}
                            onClick={() => setWecomMode('manual')}
                          >
                            手动填写
                          </Button>
                        </div>

                        {wecomMode === 'scan' ? (
                          <>
                            <Alert
                              type="info"
                              showIcon
                              message="使用企微官方授权窗口完成接入"
                              description="点击下方按钮后会打开企微授权窗口，完成授权后自动回填 Bot ID 与 Secret。"
                            />
                            <Button
                              type="primary"
                              icon={<RobotOutlined />}
                              loading={connectingChannel === 'wecom_bot' && wecomAuth.status === 'pending'}
                              onClick={() => void startWecomBotAuth()}
                            >
                              发起企微授权
                            </Button>
                          </>
                        ) : (
                          <>
                            <div className="channel-form-grid">
                              {selectedChannel.fields.map((field) => renderField(selectedChannel, field))}
                            </div>
                            <Button
                              type="primary"
                              loading={connectingChannel === selectedChannel.name}
                              onClick={() => void connectSelectedChannel()}
                            >
                              接入企微机器人
                            </Button>
                          </>
                        )}

                        {wecomAuth.status !== 'idle' ? (
                          <Alert
                            type={wecomAuth.status === 'error' ? 'error' : wecomAuth.status === 'success' ? 'success' : 'info'}
                            showIcon
                            message={wecomAuth.text}
                          />
                        ) : null}
                      </Space>
                    ) : null}

                    {selectedChannel.name !== 'weixin' && selectedChannel.name !== 'wecom_bot' ? (
                      <>
                        <div className="channel-form-grid">
                          {selectedChannel.fields.map((field) => renderField(selectedChannel, field))}
                        </div>
                        <div className="channel-card-actions">
                          <Typography.Text type="secondary">
                            可直接复用已保存配置，未修改的密钥不会被覆盖。
                          </Typography.Text>
                          <Button
                            type="primary"
                            loading={connectingChannel === selectedChannel.name}
                            onClick={() => void connectSelectedChannel()}
                          >
                            发起接入
                          </Button>
                        </div>
                      </>
                    ) : null}
                  </div>
                )}
              </Space>
            )}
          </Card>
        </Col>
      </Row>
    </div>
  );
}
