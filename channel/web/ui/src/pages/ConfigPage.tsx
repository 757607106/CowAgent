import { Button, Card, Col, Form, Input, InputNumber, Row, Select, Space, Switch, Typography, message } from 'antd';
import { useEffect, useMemo, useState } from 'react';
import { JsonBlock } from '../components/JsonBlock';
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

export default function ConfigPage() {
  const [agentForm] = Form.useForm<AgentFormShape>();

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

  const [apiBase, setApiBase] = useState('');
  const [apiKey, setApiKey] = useState('');
  const [apiKeyMasked, setApiKeyMasked] = useState(false);
  const [apiKeyMaskedValue, setApiKeyMaskedValue] = useState('');

  const [passwordValue, setPasswordValue] = useState('');
  const [passwordMasked, setPasswordMasked] = useState(false);

  const providers = rawConfig.providers || {};
  const currentProvider = (providerId && providers[providerId]) || null;

  const modelOptions = useMemo(() => {
    const models = currentProvider?.models || [];
    return [...models.map((item) => ({ label: item, value: item })), { label: '自定义模型', value: '__custom__' }];
  }, [currentProvider]);

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
      } else {
        setModelValue('__custom__');
        setCustomModel(model);
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
      } else {
        setApiKey('');
        setApiKeyMaskedValue('');
        setApiKeyMasked(false);
      }

      const pwdMasked = String(data.web_password_masked || '');
      setPasswordValue(pwdMasked);
      setPasswordMasked(Boolean(pwdMasked));
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
    if (!provider) {
      setModelValue('');
      setCustomModel('');
      setApiBase('');
      setApiKey('');
      setApiKeyMasked(false);
      setApiKeyMaskedValue('');
      return;
    }

    const currentModel = modelValue === '__custom__' ? customModel.trim() : modelValue;
    if (currentModel && provider.models.includes(currentModel)) {
      setModelValue(currentModel);
      setCustomModel('');
    } else {
      setModelValue('__custom__');
      setCustomModel(currentModel);
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
    } else {
      setApiKey('');
      setApiKeyMasked(false);
      setApiKeyMaskedValue('');
    }
  };

  const saveModelConfig = async () => {
    const provider = currentProvider;
    if (!provider || !providerId) {
      message.error('请先选择模型厂商');
      return;
    }

    const selectedModel = modelValue === '__custom__' ? customModel.trim() : modelValue;
    if (!selectedModel) {
      message.error('请先选择或输入模型名称');
      return;
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
      message.success('模型配置已保存');
      await load();
    } finally {
      setSavingModel(false);
    }
  };

  const saveAgentConfig = async () => {
    const values = await agentForm.validateFields();
    setSavingAgent(true);
    try {
      await api.updateConfig({
        enable_thinking: values.enable_thinking,
        agent_max_context_tokens: values.agent_max_context_tokens,
        agent_max_context_turns: values.agent_max_context_turns,
        agent_max_steps: values.agent_max_steps,
      });
      message.success('Agent 运行参数已保存');
      await load();
    } finally {
      setSavingAgent(false);
    }
  };

  const savePasswordConfig = async () => {
    if (passwordMasked) {
      message.success('密码未变更');
      return;
    }

    setSavingPassword(true);
    try {
      await api.updateConfig({ web_password: passwordValue.trim() });
      if (passwordValue.trim()) {
        message.success('密码已更新，页面将刷新');
        window.setTimeout(() => window.location.reload(), 800);
      } else {
        message.success('密码已清除');
        await load();
      }
    } finally {
      setSavingPassword(false);
    }
  };

  return (
    <Card loading={loading}>
      <PageTitle
        title="系统配置"
        description="按厂商维护模型接入参数，并配置 Agent 运行策略。"
        extra={<Button onClick={() => void load()}>刷新</Button>}
      />

      <Space direction="vertical" style={{ width: '100%' }} size={12}>
        <Card title="模型与供应商" bodyStyle={{ paddingBottom: 14 }}>
          <Row gutter={12}>
            <Col xs={24} md={8}>
              <Typography.Text type="secondary">模型厂商</Typography.Text>
              <Select
                style={{ width: '100%', marginTop: 6 }}
                value={providerId || undefined}
                options={Object.entries(providers).map(([id, provider]) => ({
                  value: id,
                  label: provider.label,
                }))}
                onChange={switchProvider}
                placeholder="请选择厂商"
              />
            </Col>

            <Col xs={24} md={8}>
              <Typography.Text type="secondary">模型</Typography.Text>
              <Select
                style={{ width: '100%', marginTop: 6 }}
                value={modelValue || undefined}
                options={modelOptions}
                onChange={(value) => setModelValue(value)}
                placeholder="请选择模型"
                disabled={!currentProvider}
              />
            </Col>

            <Col xs={24} md={8}>
              <Typography.Text type="secondary">自定义模型</Typography.Text>
              <Input
                style={{ marginTop: 6 }}
                placeholder="仅在选择自定义模型时填写"
                value={customModel}
                disabled={modelValue !== '__custom__'}
                onChange={(event) => setCustomModel(event.target.value)}
              />
            </Col>

            <Col xs={24} md={12}>
              <Typography.Text type="secondary">API Base</Typography.Text>
              <Input
                style={{ marginTop: 6 }}
                placeholder={currentProvider?.api_base_default || '当前厂商无需配置'}
                value={apiBase}
                disabled={!currentProvider?.api_base_key}
                onChange={(event) => setApiBase(event.target.value)}
              />
            </Col>

            <Col xs={24} md={12}>
              <Typography.Text type="secondary">API Key</Typography.Text>
              <Input.Password
                style={{ marginTop: 6 }}
                value={apiKey}
                disabled={!currentProvider?.api_key_field}
                placeholder={currentProvider?.api_key_field ? '保持为空表示不修改' : '当前厂商无需配置'}
                onFocus={() => {
                  if (apiKeyMasked) {
                    setApiKey('');
                    setApiKeyMasked(false);
                  }
                }}
                onBlur={() => {
                  if (!apiKey.trim() && apiKeyMaskedValue) {
                    setApiKey(apiKeyMaskedValue);
                    setApiKeyMasked(true);
                  }
                }}
                onChange={(event) => {
                  setApiKey(event.target.value);
                  setApiKeyMasked(false);
                }}
              />
            </Col>
          </Row>

          <Space style={{ marginTop: 14 }}>
            <Button type="primary" loading={savingModel} onClick={() => void saveModelConfig()}>保存模型配置</Button>
          </Space>
        </Card>

        <Card title="Agent 运行参数" bodyStyle={{ paddingBottom: 14 }}>
          <Form form={agentForm} layout="vertical">
            <Row gutter={12}>
              <Col xs={24} md={6}>
                <Form.Item name="enable_thinking" label="启用思考过程" valuePropName="checked">
                  <Switch />
                </Form.Item>
              </Col>
              <Col xs={24} md={6}>
                <Form.Item name="agent_max_context_tokens" label="最大上下文 Tokens" rules={[{ required: true }]}> 
                  <InputNumber min={1024} step={1024} style={{ width: '100%' }} />
                </Form.Item>
              </Col>
              <Col xs={24} md={6}>
                <Form.Item name="agent_max_context_turns" label="最大上下文轮次" rules={[{ required: true }]}> 
                  <InputNumber min={1} max={200} style={{ width: '100%' }} />
                </Form.Item>
              </Col>
              <Col xs={24} md={6}>
                <Form.Item name="agent_max_steps" label="最大执行步数" rules={[{ required: true }]}> 
                  <InputNumber min={1} max={200} style={{ width: '100%' }} />
                </Form.Item>
              </Col>
            </Row>
          </Form>
          <Button type="primary" loading={savingAgent} onClick={() => void saveAgentConfig()}>保存 Agent 参数</Button>
        </Card>

        <Card title="控制台密码" bodyStyle={{ paddingBottom: 14 }}>
          <Typography.Paragraph type="secondary">
            留空可清除密码；已掩码状态表示当前已有密码但未修改。
          </Typography.Paragraph>
          <Space.Compact style={{ width: 420, maxWidth: '100%' }}>
            <Input.Password
              value={passwordValue}
              placeholder="输入新密码"
              onFocus={() => {
                if (passwordMasked) {
                  setPasswordValue('');
                  setPasswordMasked(false);
                }
              }}
              onChange={(event) => {
                setPasswordValue(event.target.value);
                setPasswordMasked(false);
              }}
            />
            <Button type="primary" loading={savingPassword} onClick={() => void savePasswordConfig()}>保存</Button>
          </Space.Compact>
        </Card>

        <Card title="配置原始数据">
          <JsonBlock value={rawConfig} />
        </Card>
      </Space>
    </Card>
  );
}
