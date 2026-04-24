import { Alert, Button, Card, Col, Form, Input, InputNumber, Row, Select, Space, Switch, Tag, Typography, message } from 'antd';
import { useEffect, useMemo, useState } from 'react';
import { PageTitle } from '../components/PageTitle';
import { api } from '../services/api';

interface ProviderDef {
  label: string;
  models: string[];
  api_base_key?: string | null;
  api_base_default?: string | null;
  api_key_field?: string | null;
}

interface ConfigShape {
  model: string;
  bot_type?: string;
  use_linkai?: boolean;
  enable_thinking: boolean;
  agent_max_context_tokens: number;
  agent_max_context_turns: number;
  agent_max_steps: number;
  web_password_masked?: string;
  providers?: Record<string, ProviderDef>;
  api_bases?: Record<string, string>;
  api_keys?: Record<string, string>;
}

interface AgentFormShape {
  enable_thinking: boolean;
  agent_max_context_tokens: number;
  agent_max_context_turns: number;
  agent_max_steps: number;
}

interface StatusMeta {
  text: string;
  color: 'success' | 'processing' | 'warning' | 'default';
}

const AGENT_PRESETS: Array<{ key: string; label: string; description: string; values: AgentFormShape }> = [
  {
    key: 'stable',
    label: '稳健默认',
    description: '适合大多数生产场景，控制成本与上下文长度。',
    values: {
      enable_thinking: false,
      agent_max_context_tokens: 32000,
      agent_max_context_turns: 12,
      agent_max_steps: 12,
    },
  },
  {
    key: 'balanced',
    label: '平衡模式',
    description: '兼顾上下文记忆与多步执行能力。',
    values: {
      enable_thinking: true,
      agent_max_context_tokens: 50000,
      agent_max_context_turns: 20,
      agent_max_steps: 20,
    },
  },
  {
    key: 'reasoning',
    label: '高推理模式',
    description: '适合复杂任务调试，成本更高。',
    values: {
      enable_thinking: true,
      agent_max_context_tokens: 65536,
      agent_max_context_turns: 30,
      agent_max_steps: 32,
    },
  },
];

function detectProvider(data: ConfigShape): string {
  const providers = data.providers || {};
  const providerIds = Object.keys(providers);
  if (providerIds.length === 0) return '';

  if (data.use_linkai && providers.linkai) return 'linkai';
  if (data.bot_type && providers[data.bot_type]) return data.bot_type;

  const model = String(data.model || '');
  if (model) {
    for (const [providerId, provider] of Object.entries(providers)) {
      if ((provider.models || []).includes(model)) return providerId;
    }
  }

  return providerIds[0] || '';
}

function buildModelStatus(args: {
  providerId: string;
  selectedModel: string;
  requiresApiKey: boolean;
  apiKeyMaskedValue: string;
  apiKeyValue: string;
  isDirty: boolean;
}): StatusMeta {
  if (!args.providerId) {
    return { text: '待选择供应商', color: 'default' };
  }
  if (!args.selectedModel) {
    return { text: '待补充模型', color: 'warning' };
  }
  if (args.requiresApiKey && !args.apiKeyMaskedValue && !args.apiKeyValue.trim()) {
    return { text: '待填写 API Key', color: 'warning' };
  }
  if (args.isDirty) {
    return { text: '有未保存改动', color: 'processing' };
  }
  return { text: '已配置', color: 'success' };
}

function buildSecurityStatus(passwordMasked: boolean, passwordTouched: boolean, passwordValue: string): StatusMeta {
  if (passwordTouched) {
    return passwordValue.trim()
      ? { text: '待更新密码', color: 'processing' }
      : { text: '待清除密码', color: 'warning' };
  }
  return passwordMasked ? { text: '已设置密码', color: 'success' } : { text: '未设置密码', color: 'default' };
}

export default function ConfigPage() {
  const [agentForm] = Form.useForm<AgentFormShape>();
  const agentValues = Form.useWatch([], agentForm);

  const [loading, setLoading] = useState(false);
  const [savingModel, setSavingModel] = useState(false);
  const [savingAgent, setSavingAgent] = useState(false);
  const [savingPassword, setSavingPassword] = useState(false);

  const [rawConfig, setRawConfig] = useState<ConfigShape>({
    model: '',
    enable_thinking: true,
    agent_max_context_tokens: 50000,
    agent_max_context_turns: 20,
    agent_max_steps: 20,
  });

  const [providerId, setProviderId] = useState('');
  const [modelValue, setModelValue] = useState('');
  const [customModel, setCustomModel] = useState('');
  const [useCustomModel, setUseCustomModel] = useState(false);

  const [apiBase, setApiBase] = useState('');
  const [apiKey, setApiKey] = useState('');
  const [apiKeyMasked, setApiKeyMasked] = useState(false);
  const [apiKeyMaskedValue, setApiKeyMaskedValue] = useState('');
  const [apiKeyTouched, setApiKeyTouched] = useState(false);

  const [passwordValue, setPasswordValue] = useState('');
  const [passwordMasked, setPasswordMasked] = useState(false);
  const [passwordTouched, setPasswordTouched] = useState(false);

  const providers = rawConfig.providers || {};
  const currentProvider = (providerId && providers[providerId]) || null;
  const savedProviderId = useMemo(() => detectProvider(rawConfig), [rawConfig]);
  const isProviderWithoutPresetModels = Boolean(currentProvider && (currentProvider.models || []).length === 0);
  const isCustomModelActive = useCustomModel || isProviderWithoutPresetModels;
  const selectedModelName = (isCustomModelActive ? customModel : modelValue).trim();

  const modelOptions = useMemo(() => {
    const models = currentProvider?.models || [];
    return models.map((item) => ({ label: item, value: item }));
  }, [currentProvider]);

  const savedApiBase = useMemo(() => {
    if (!currentProvider?.api_base_key) return '';
    return String(rawConfig.api_bases?.[currentProvider.api_base_key] || currentProvider.api_base_default || '').trim();
  }, [currentProvider, rawConfig.api_bases]);

  const modelConfigDirty = useMemo(() => {
    if (!providerId) return false;
    if (providerId !== savedProviderId) return true;
    if (selectedModelName !== String(rawConfig.model || '').trim()) return true;
    if ((currentProvider?.api_base_key ? apiBase.trim() : '') !== savedApiBase) return true;
    if (currentProvider?.api_key_field && apiKeyTouched && Boolean(apiKey.trim())) return true;
    return false;
  }, [apiBase, apiKey, apiKeyTouched, currentProvider, providerId, rawConfig.model, savedApiBase, savedProviderId, selectedModelName]);

  const agentConfigDirty = useMemo(() => {
    if (!agentValues) return false;
    return (
      Boolean(agentValues.enable_thinking) !== Boolean(rawConfig.enable_thinking ?? true)
      || Number(agentValues.agent_max_context_tokens || 0) !== Number(rawConfig.agent_max_context_tokens || 50000)
      || Number(agentValues.agent_max_context_turns || 0) !== Number(rawConfig.agent_max_context_turns || 20)
      || Number(agentValues.agent_max_steps || 0) !== Number(rawConfig.agent_max_steps || 20)
    );
  }, [agentValues, rawConfig]);

  const passwordConfigDirty = passwordTouched;
  const hasPendingChanges = modelConfigDirty || agentConfigDirty || passwordConfigDirty;

  const modelStatus = buildModelStatus({
    providerId,
    selectedModel: selectedModelName,
    requiresApiKey: Boolean(currentProvider?.api_key_field),
    apiKeyMaskedValue,
    apiKeyValue: apiKey,
    isDirty: modelConfigDirty,
  });
  const securityStatus = buildSecurityStatus(passwordMasked, passwordTouched, passwordValue);

  const load = async () => {
    setLoading(true);
    try {
      const data = await api.getConfig() as ConfigShape;
      setRawConfig(data);

      agentForm.setFieldsValue({
        enable_thinking: Boolean(data.enable_thinking ?? true),
        agent_max_context_tokens: Number(data.agent_max_context_tokens || 50000),
        agent_max_context_turns: Number(data.agent_max_context_turns || 20),
        agent_max_steps: Number(data.agent_max_steps || 20),
      });

      const detectedProvider = detectProvider(data);
      setProviderId(detectedProvider);

      const provider = data.providers?.[detectedProvider];
      const model = String(data.model || '');
      if (provider && provider.models.includes(model)) {
        setModelValue(model);
        setCustomModel('');
        setUseCustomModel(false);
      } else {
        setModelValue(provider?.models?.[0] || '');
        setCustomModel(model);
        setUseCustomModel(Boolean(model) || Boolean(provider && provider.models.length === 0));
      }

      if (provider?.api_base_key) {
        setApiBase(String(data.api_bases?.[provider.api_base_key] || provider.api_base_default || ''));
      } else {
        setApiBase('');
      }

      if (provider?.api_key_field) {
        const maskedValue = String(data.api_keys?.[provider.api_key_field] || '');
        setApiKey(maskedValue);
        setApiKeyMaskedValue(maskedValue);
        setApiKeyMasked(Boolean(maskedValue));
        setApiKeyTouched(false);
      } else {
        setApiKey('');
        setApiKeyMaskedValue('');
        setApiKeyMasked(false);
        setApiKeyTouched(false);
      }

      const pwdMasked = String(data.web_password_masked || '');
      setPasswordValue(pwdMasked);
      setPasswordMasked(Boolean(pwdMasked));
      setPasswordTouched(false);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, []);

  const switchProvider = (nextProviderId: string) => {
    setProviderId(nextProviderId);
    const provider = providers[nextProviderId];
    const currentResolvedModel = selectedModelName;
    if (!provider) {
      setModelValue('');
      setCustomModel('');
      setUseCustomModel(false);
      setApiBase('');
      setApiKey('');
      setApiKeyMasked(false);
      setApiKeyMaskedValue('');
      setApiKeyTouched(false);
      return;
    }

    if (currentResolvedModel && provider.models.includes(currentResolvedModel)) {
      setModelValue(currentResolvedModel);
      setCustomModel('');
      setUseCustomModel(false);
    } else {
      setModelValue(provider.models[0] || '');
      setCustomModel(currentResolvedModel);
      setUseCustomModel(Boolean(currentResolvedModel) || provider.models.length === 0);
    }

    if (provider.api_base_key) {
      setApiBase(String(rawConfig.api_bases?.[provider.api_base_key] || provider.api_base_default || ''));
    } else {
      setApiBase('');
    }

    if (provider.api_key_field) {
      const maskedValue = String(rawConfig.api_keys?.[provider.api_key_field] || '');
      setApiKey(maskedValue);
      setApiKeyMaskedValue(maskedValue);
      setApiKeyMasked(Boolean(maskedValue));
      setApiKeyTouched(false);
    } else {
      setApiKey('');
      setApiKeyMasked(false);
      setApiKeyMaskedValue('');
      setApiKeyTouched(false);
    }
  };

  const saveModelConfig = async (reloadAfterSave = true) => {
    const provider = currentProvider;
    if (!provider || !providerId) {
      message.error('请先选择模型厂商');
      return false;
    }

    const selectedModel = selectedModelName;
    if (!selectedModel) {
      message.error('请先选择或输入模型名称');
      return false;
    }

    const updates: Record<string, unknown> = {
      model: selectedModel,
      use_linkai: providerId === 'linkai',
      bot_type: providerId === 'linkai' ? '' : providerId,
    };

    if (provider.api_base_key) {
      const value = apiBase.trim();
      if (value) updates[provider.api_base_key] = value;
    }

    if (provider.api_key_field) {
      const value = apiKey.trim();
      if (value && !apiKeyMasked) {
        updates[provider.api_key_field] = value;
      }
    }

    setSavingModel(true);
    try {
      await api.updateConfig(updates);
      if (reloadAfterSave) {
        message.success('模型配置已保存');
        await load();
      }
      return true;
    } finally {
      setSavingModel(false);
    }
  };

  const saveAgentConfig = async (reloadAfterSave = true) => {
    const values = await agentForm.validateFields();
    setSavingAgent(true);
    try {
      await api.updateConfig({
        enable_thinking: values.enable_thinking,
        agent_max_context_tokens: values.agent_max_context_tokens,
        agent_max_context_turns: values.agent_max_context_turns,
        agent_max_steps: values.agent_max_steps,
      });
      if (reloadAfterSave) {
        message.success('Agent 运行参数已保存');
        await load();
      }
      return true;
    } finally {
      setSavingAgent(false);
    }
  };

  const savePasswordConfig = async (reloadAfterSave = true) => {
    if (!passwordTouched && passwordMasked) {
      message.success('密码未变更');
      return true;
    }

    setSavingPassword(true);
    try {
      await api.updateConfig({ web_password: passwordValue.trim() });
      if (passwordValue.trim()) {
        if (reloadAfterSave) {
          message.success('密码已更新，页面将刷新');
          window.setTimeout(() => window.location.reload(), 800);
        }
      } else {
        if (reloadAfterSave) {
          message.success('密码已清除');
          await load();
        }
      }
      return true;
    } finally {
      setSavingPassword(false);
    }
  };

  const saveAllChanges = async () => {
    if (!hasPendingChanges) {
      message.info('当前没有需要保存的改动');
      return;
    }

    if (modelConfigDirty) {
      const ok = await saveModelConfig(false);
      if (!ok) return;
    }
    if (agentConfigDirty) {
      await saveAgentConfig(false);
    }
    if (passwordConfigDirty) {
      await savePasswordConfig(false);
    }

    message.success('配置已更新');
    if (passwordTouched && passwordValue.trim()) {
      window.setTimeout(() => window.location.reload(), 800);
      return;
    }
    await load();
  };

  const applyAgentPreset = (preset: AgentFormShape) => {
    agentForm.setFieldsValue(preset);
  };

  return (
    <div className="config-page">
      <Card loading={loading} className="config-shell">
        <PageTitle
          title="系统配置"
          description="优先完成模型接入，再配置 Agent 运行策略与控制台安全项。"
          extra={(
            <Space wrap>
              <Button onClick={() => void load()}>刷新</Button>
              <Button type="primary" disabled={!hasPendingChanges} onClick={() => void saveAllChanges()}>
                保存全部更改
              </Button>
            </Space>
          )}
        />

        <div className="config-overview">
          <div className="config-overview-card">
            <Typography.Text type="secondary">当前供应商</Typography.Text>
            <Typography.Title level={5}>{currentProvider?.label || '未选择'}</Typography.Title>
          </div>
          <div className="config-overview-card">
            <Typography.Text type="secondary">当前模型</Typography.Text>
            <Typography.Title level={5}>{selectedModelName || '待配置'}</Typography.Title>
          </div>
          <div className="config-overview-card">
            <Typography.Text type="secondary">API Key</Typography.Text>
            <Space size={8} wrap>
              <Tag color={currentProvider?.api_key_field ? (apiKeyMaskedValue ? 'success' : 'warning') : 'default'}>
                {currentProvider?.api_key_field ? (apiKeyMaskedValue ? '已配置' : '待填写') : '当前无需配置'}
              </Tag>
              {isCustomModelActive ? <Tag color="processing">自定义模型</Tag> : null}
            </Space>
          </div>
          <div className="config-overview-card">
            <Typography.Text type="secondary">页面状态</Typography.Text>
            <Space size={8} wrap>
              <Tag color={hasPendingChanges ? 'processing' : 'success'}>
                {hasPendingChanges ? '有未保存更改' : '已同步'}
              </Tag>
              <Tag color={securityStatus.color}>{securityStatus.text}</Tag>
            </Space>
          </div>
        </div>

        <Space direction="vertical" style={{ width: '100%' }} size={16}>
          <Card
            title="模型接入"
            extra={<Tag color={modelStatus.color}>{modelStatus.text}</Tag>}
            className="config-section-card"
          >
            <Typography.Paragraph type="secondary" className="config-section-intro">
              按“选择供应商 - 填连接信息 - 确认模型”的顺序完成配置；只有启用自定义模型时，额外名称输入框才会展开。
            </Typography.Paragraph>

            <div className="config-step-block">
              <div className="config-step-head">
                <span className="config-step-index">01</span>
                <div>
                  <Typography.Title level={5}>选择供应商与基础模型</Typography.Title>
                  <Typography.Text type="secondary">优先使用厂商预置模型，减少手填成本。</Typography.Text>
                </div>
              </div>
              <Row gutter={[16, 16]}>
                <Col xs={24} lg={10}>
                  <Typography.Text className="config-field-label">模型厂商</Typography.Text>
                  <Select
                    style={{ width: '100%', marginTop: 8 }}
                    value={providerId || undefined}
                    options={Object.entries(providers).map(([id, provider]) => ({
                      value: id,
                      label: provider.label,
                    }))}
                    onChange={switchProvider}
                    placeholder="请选择厂商"
                  />
                  <Typography.Paragraph type="secondary" className="config-field-help">
                    切换厂商时会自动带出已保存的地址与密钥状态。
                  </Typography.Paragraph>
                </Col>
                <Col xs={24} lg={14}>
                  <Typography.Text className="config-field-label">标准模型</Typography.Text>
                  <Select
                    style={{ width: '100%', marginTop: 8 }}
                    value={modelValue || undefined}
                    options={modelOptions}
                    onChange={(value) => setModelValue(value)}
                    placeholder={currentProvider ? '请选择模型' : '请先选择厂商'}
                    disabled={!currentProvider || isCustomModelActive}
                  />
                  <Typography.Paragraph type="secondary" className="config-field-help">
                    {isCustomModelActive ? '已切换为自定义模型模式，标准模型选择暂时关闭。' : '当厂商提供固定模型列表时，优先从下拉中选择。'}
                  </Typography.Paragraph>
                </Col>
              </Row>
            </div>

            <div className="config-step-block">
              <div className="config-step-head">
                <span className="config-step-index">02</span>
                <div>
                  <Typography.Title level={5}>连接凭证</Typography.Title>
                  <Typography.Text type="secondary">将连接地址与密钥放在同一组，减少来回跳读。</Typography.Text>
                </div>
              </div>
              <Row gutter={[16, 16]}>
                <Col xs={24} lg={12}>
                  <Typography.Text className="config-field-label">API Base</Typography.Text>
                  <Input
                    style={{ marginTop: 8 }}
                    placeholder={currentProvider?.api_base_default || '当前厂商无需配置'}
                    value={apiBase}
                    disabled={!currentProvider?.api_base_key}
                    onChange={(event) => setApiBase(event.target.value)}
                  />
                  <Typography.Paragraph type="secondary" className="config-field-help">
                    {currentProvider?.api_base_key
                      ? `留空时建议使用默认地址：${currentProvider.api_base_default || '由服务端维护'}`
                      : '该厂商当前不需要单独配置 API Base。'}
                  </Typography.Paragraph>
                </Col>

                <Col xs={24} lg={12}>
                  <Typography.Text className="config-field-label">API Key</Typography.Text>
                  <Input.Password
                    style={{ marginTop: 8 }}
                    value={apiKey}
                    disabled={!currentProvider?.api_key_field}
                    placeholder={currentProvider?.api_key_field ? '已保存时保持为空表示不覆盖' : '当前厂商无需配置'}
                    onFocus={() => {
                      if (apiKeyMasked) {
                        setApiKey('');
                        setApiKeyMasked(false);
                      }
                    }}
                    onBlur={() => {
                      if (!apiKey.trim() && apiKeyMaskedValue && !apiKeyTouched) {
                        setApiKey(apiKeyMaskedValue);
                        setApiKeyMasked(true);
                      }
                    }}
                    onChange={(event) => {
                      setApiKey(event.target.value);
                      setApiKeyMasked(false);
                      setApiKeyTouched(true);
                    }}
                  />
                  <Typography.Paragraph type="secondary" className="config-field-help">
                    {currentProvider?.api_key_field
                      ? (apiKeyMaskedValue ? '已存在密钥时，重新输入才会覆盖当前值。' : '首次接入时需要填写有效的 API Key。')
                      : '当前厂商未启用 API Key 字段。'}
                  </Typography.Paragraph>
                </Col>
              </Row>
            </div>

            <div className="config-step-block">
              <div className="config-step-head">
                <span className="config-step-index">03</span>
                <div>
                  <Typography.Title level={5}>自定义模型</Typography.Title>
                  <Typography.Text type="secondary">仅在下拉列表没有目标模型时启用，避免无效输入。</Typography.Text>
                </div>
              </div>

              <div className="config-custom-toggle">
                <div>
                  <Typography.Text strong>使用自定义模型名称</Typography.Text>
                  <Typography.Paragraph type="secondary" className="config-field-help">
                    适用于厂商列表尚未内置的新模型或兼容 OpenAI 协议的自定义端点。
                  </Typography.Paragraph>
                </div>
                <Switch
                  checked={isCustomModelActive}
                  disabled={!currentProvider}
                  onChange={(checked) => {
                    if (!currentProvider) return;
                    setUseCustomModel(checked);
                    if (checked) {
                      setCustomModel((value) => value || modelValue);
                    } else if (currentProvider.models.includes(customModel.trim())) {
                      setModelValue(customModel.trim());
                      setCustomModel('');
                    } else {
                      setModelValue(currentProvider.models[0] || '');
                    }
                  }}
                />
              </div>

              {isCustomModelActive ? (
                <div className="config-custom-panel">
                  <Typography.Text className="config-field-label">自定义模型名称</Typography.Text>
                  <Input
                    style={{ marginTop: 8 }}
                    placeholder="例如：gpt-4.1-mini / qwen-max-latest"
                    value={customModel}
                    onChange={(event) => setCustomModel(event.target.value)}
                  />
                  <Typography.Paragraph type="secondary" className="config-field-help">
                    保存时将以这个名称写入当前模型配置，不再依赖预置下拉选项。
                  </Typography.Paragraph>
                </div>
              ) : null}

              <Alert
                type={modelStatus.color === 'warning' ? 'warning' : modelStatus.color === 'success' ? 'success' : 'info'}
                showIcon
                message={modelStatus.text}
                description={(
                  currentProvider?.api_key_field
                    ? '请确认厂商、模型与凭证一起保存，避免只改模型但忘记同步 API Key。'
                    : '当前厂商不依赖单独的 API Key 字段，可直接保存模型与地址设置。'
                )}
              />
            </div>

            <div className="config-section-actions">
              <Button loading={savingModel} onClick={() => void load()}>重置本区改动</Button>
              <Button type="primary" loading={savingModel} onClick={() => void saveModelConfig()}>
                保存模型接入
              </Button>
            </div>
          </Card>

          <Card
            title="运行策略"
            extra={<Tag color={agentConfigDirty ? 'processing' : 'success'}>{agentConfigDirty ? '待保存' : '已同步'}</Tag>}
            className="config-section-card"
          >
            <Typography.Paragraph type="secondary" className="config-section-intro">
              先选一个接近的推荐预设，再按需微调，避免一开始就直接修改所有参数。
            </Typography.Paragraph>

            <div className="config-presets">
              {AGENT_PRESETS.map((preset) => (
                <button
                  key={preset.key}
                  type="button"
                  className="config-preset-button"
                  onClick={() => applyAgentPreset(preset.values)}
                >
                  <span className="config-preset-title">{preset.label}</span>
                  <span className="config-preset-desc">{preset.description}</span>
                </button>
              ))}
            </div>

            <Form form={agentForm} layout="vertical">
              <Row gutter={[16, 8]}>
                <Col xs={24} lg={6}>
                  <div className="config-setting-tile">
                    <Form.Item name="enable_thinking" label="启用思考过程" valuePropName="checked" style={{ marginBottom: 0 }}>
                      <Switch />
                    </Form.Item>
                    <Typography.Paragraph type="secondary" className="config-field-help">
                      开启后适合调试复杂任务；正式场景可按需关闭，减少过程展示。
                    </Typography.Paragraph>
                  </div>
                </Col>
                <Col xs={24} lg={6}>
                  <div className="config-setting-tile">
                    <Form.Item name="agent_max_context_tokens" label="最大上下文 Tokens" rules={[{ required: true }]}>
                      <InputNumber min={1024} step={1024} style={{ width: '100%' }} />
                    </Form.Item>
                    <Typography.Paragraph type="secondary" className="config-field-help">
                      值越大，历史上下文保留越多，但推理成本也更高。
                    </Typography.Paragraph>
                  </div>
                </Col>
                <Col xs={24} lg={6}>
                  <div className="config-setting-tile">
                    <Form.Item name="agent_max_context_turns" label="最大上下文轮次" rules={[{ required: true }]}>
                      <InputNumber min={1} max={200} style={{ width: '100%' }} />
                    </Form.Item>
                    <Typography.Paragraph type="secondary" className="config-field-help">
                      控制历史对话回看范围，适合平衡记忆与响应速度。
                    </Typography.Paragraph>
                  </div>
                </Col>
                <Col xs={24} lg={6}>
                  <div className="config-setting-tile">
                    <Form.Item name="agent_max_steps" label="最大执行步数" rules={[{ required: true }]}>
                      <InputNumber min={1} max={200} style={{ width: '100%' }} />
                    </Form.Item>
                    <Typography.Paragraph type="secondary" className="config-field-help">
                      限制工具调用和链路深度，过大可能导致任务执行过长。
                    </Typography.Paragraph>
                  </div>
                </Col>
              </Row>
            </Form>

            <div className="config-section-actions">
              <Button onClick={() => applyAgentPreset(AGENT_PRESETS[1].values)}>恢复平衡模式</Button>
              <Button type="primary" loading={savingAgent} onClick={() => void saveAgentConfig()}>
                保存运行策略
              </Button>
            </div>
          </Card>

          <Card
            title="安全设置"
            extra={<Tag color={securityStatus.color}>{securityStatus.text}</Tag>}
            className="config-section-card"
          >
            <Typography.Paragraph type="secondary" className="config-section-intro">
              用于控制控制台访问。已掩码表示当前已有密码；重新输入才会覆盖，清空后保存则表示移除访问密码。
            </Typography.Paragraph>

            <div className="config-security-panel">
              <Space.Compact style={{ width: '100%', maxWidth: 460 }}>
                <Input.Password
                  value={passwordValue}
                  placeholder={passwordMasked ? '输入新密码以覆盖当前值，留空并保存可清除' : '输入新密码'}
                  onFocus={() => {
                    if (passwordMasked) {
                      setPasswordValue('');
                      setPasswordMasked(false);
                    }
                  }}
                  onChange={(event) => {
                    setPasswordValue(event.target.value);
                    setPasswordMasked(false);
                    setPasswordTouched(true);
                  }}
                />
                <Button type="primary" loading={savingPassword} onClick={() => void savePasswordConfig()}>
                  更新密码
                </Button>
              </Space.Compact>
              <Typography.Paragraph type="secondary" className="config-field-help">
                当前状态：{passwordMasked ? '已设置访问密码。' : '未设置访问密码。'}
              </Typography.Paragraph>
            </div>
          </Card>

          {hasPendingChanges ? (
            <div className="config-sticky-bar">
              <div>
                <Typography.Text strong>检测到未保存变更</Typography.Text>
                <Typography.Paragraph type="secondary" style={{ margin: 0 }}>
                  建议一次性保存，避免模型接入、运行策略和密码状态不一致。
                </Typography.Paragraph>
              </div>
              <Space wrap>
                <Button onClick={() => void load()}>取消修改</Button>
                <Button type="primary" onClick={() => void saveAllChanges()}>
                  保存全部更改
                </Button>
              </Space>
            </div>
          ) : null}
        </Space>
      </Card>
    </div>
  );
}
