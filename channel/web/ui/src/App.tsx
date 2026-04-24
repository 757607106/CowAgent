import {
  ApiOutlined,
  ApartmentOutlined,
  AppstoreOutlined,
  BuildOutlined,
  ClusterOutlined,
  DatabaseOutlined,
  FileSearchOutlined,
  FileTextOutlined,
  HddOutlined,
  MessageOutlined,
  ScheduleOutlined,
  SettingOutlined,
  TeamOutlined,
  ToolOutlined,
} from '@ant-design/icons';
import { App as AntdApp, Button, ConfigProvider, Form, Input, Layout, Menu, Spin, Typography, message } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { HashRouter, Navigate, Route, Routes, useLocation, useNavigate } from 'react-router-dom';
import { XProvider } from '@ant-design/x';
import xZhCN from '@ant-design/x/locale/zh_CN';
import ChatPage from './pages/ChatPage';
import ConfigPage from './pages/ConfigPage';
import ToolsPage from './pages/ToolsPage';
import SkillsPage from './pages/SkillsPage';
import McpPage from './pages/McpPage';
import AgentsPage from './pages/AgentsPage';
import BindingsPage from './pages/BindingsPage';
import TenantsPage from './pages/TenantsPage';
import TenantUsersPage from './pages/TenantUsersPage';
import MemoryPage from './pages/MemoryPage';
import KnowledgePage from './pages/KnowledgePage';
import ChannelsPage from './pages/ChannelsPage';
import TasksPage from './pages/TasksPage';
import LogsPage from './pages/LogsPage';
import { RuntimeContext, WORKSPACE_AGENT_VALUE, type RuntimeAgentOption } from './context/runtime';
import { api } from './services/api';
import type { RuntimeScope } from './types';

const { Sider, Content } = Layout;

const AGENT_KEY = 'cowagent_runtime_agent_id';
const BINDING_KEY = 'cowagent_runtime_binding_id';

const menuItems = [
  { key: '/chat', icon: <MessageOutlined />, label: '对话' },
  { key: '/config', icon: <SettingOutlined />, label: '配置' },
  { key: '/tools', icon: <ToolOutlined />, label: '工具' },
  { key: '/skills', icon: <BuildOutlined />, label: '技能' },
  { key: '/mcp', icon: <ApiOutlined />, label: 'MCP' },
  { key: '/agents', icon: <AppstoreOutlined />, label: '智能体' },
  { key: '/bindings', icon: <ClusterOutlined />, label: '绑定' },
  { key: '/tenants', icon: <ApartmentOutlined />, label: '租户' },
  { key: '/tenant-users', icon: <TeamOutlined />, label: '租户成员' },
  { key: '/memory', icon: <DatabaseOutlined />, label: '记忆' },
  { key: '/knowledge', icon: <FileSearchOutlined />, label: '知识库' },
  { key: '/channels', icon: <HddOutlined />, label: '渠道' },
  { key: '/tasks', icon: <ScheduleOutlined />, label: '任务' },
  { key: '/logs', icon: <FileTextOutlined />, label: '日志' },
];

function LoginScreen({ onLogin }: { onLogin: () => Promise<void> }) {
  const [form] = Form.useForm<{ password: string }>();
  const [submitting, setSubmitting] = useState(false);

  const submit = async () => {
    const { password } = await form.validateFields();
    setSubmitting(true);
    try {
      await api.login(password);
      await onLogin();
      message.success('登录成功');
    } catch (error) {
      message.error(error instanceof Error ? error.message : '登录失败');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="app-login-wrap">
      <div className="app-login-panel">
        <Typography.Title level={3} style={{ marginTop: 0 }}>CowAgent 控制台</Typography.Title>
        <Typography.Paragraph type="secondary">请输入控制台密码继续访问。</Typography.Paragraph>
        <Form form={form} layout="vertical">
          <Form.Item name="password" label="密码" rules={[{ required: true, message: '请输入密码' }]}>
            <Input.Password onPressEnter={() => void submit()} />
          </Form.Item>
          <Button type="primary" block loading={submitting} onClick={() => void submit()}>登录</Button>
        </Form>
      </div>
    </div>
  );
}

function Shell() {
  const navigate = useNavigate();
  const location = useLocation();

  const [scope, setScope] = useState<RuntimeScope>({
    agentId: localStorage.getItem(AGENT_KEY) || '',
    bindingId: '',
  });
  const [agentOptions, setAgentOptions] = useState<RuntimeAgentOption[]>([]);

  const loadRuntimeOptions = useCallback(async () => {
    const agentData = await api.listAgentsSimple();
    setAgentOptions([
      { label: '默认助手（当前工作区）', value: WORKSPACE_AGENT_VALUE },
      ...(agentData.agents || []).map((agent) => {
        const isDefaultAgent = agent.agent_id === 'default';
        const label = isDefaultAgent
          ? `${agent.name}（默认智能体 / ${agent.agent_id}）`
          : `${agent.name} (${agent.agent_id})`;
        return { label, value: agent.agent_id };
      }),
    ]);
  }, []);

  useEffect(() => {
    localStorage.removeItem(BINDING_KEY);
    void loadRuntimeOptions();
  }, [loadRuntimeOptions]);

  const setAgentScope = useCallback((value?: string) => {
    const resolvedAgentId = !value || value === WORKSPACE_AGENT_VALUE ? '' : value;
    const next = { agentId: resolvedAgentId, bindingId: '' };
    setScope(next);
    localStorage.removeItem(BINDING_KEY);
    if (next.agentId) {
      localStorage.setItem(AGENT_KEY, next.agentId);
    } else {
      localStorage.removeItem(AGENT_KEY);
    }
  }, []);

  const selectedMenu = useMemo(() => {
    const target = menuItems.find((item) => location.pathname.startsWith(item.key));
    return target ? [target.key] : ['/chat'];
  }, [location.pathname]);

  return (
    <RuntimeContext.Provider
      value={{
        scope,
        setScope,
        agentOptions,
        refreshAgentOptions: loadRuntimeOptions,
        setAgentScope,
      }}
    >
      <Layout className="app-layout">
        <Sider width={220} theme="light">
          <div className="app-logo">CowAgent 2.0.6</div>
          <Menu
            mode="inline"
            selectedKeys={selectedMenu}
            items={menuItems}
            onClick={({ key }) => navigate(String(key))}
            style={{ borderInlineEnd: 0 }}
          />
        </Sider>
        <Layout>
          <Content className="app-content">
            <Routes>
              <Route path="/" element={<Navigate to="/chat" replace />} />
              <Route path="/chat" element={<ChatPage />} />
              <Route path="/config" element={<ConfigPage />} />
              <Route path="/tools" element={<ToolsPage />} />
              <Route path="/skills" element={<SkillsPage />} />
              <Route path="/mcp" element={<McpPage />} />
              <Route path="/agents" element={<AgentsPage />} />
              <Route path="/bindings" element={<BindingsPage />} />
              <Route path="/tenants" element={<TenantsPage />} />
              <Route path="/tenant-users" element={<TenantUsersPage />} />
              <Route path="/memory" element={<MemoryPage />} />
              <Route path="/knowledge" element={<KnowledgePage />} />
              <Route path="/channels" element={<ChannelsPage />} />
              <Route path="/tasks" element={<TasksPage />} />
              <Route path="/logs" element={<LogsPage />} />
              <Route path="*" element={<Navigate to="/chat" replace />} />
            </Routes>
          </Content>
        </Layout>
      </Layout>
    </RuntimeContext.Provider>
  );
}

export default function App() {
  const [checkingAuth, setCheckingAuth] = useState(true);
  const [authRequired, setAuthRequired] = useState(false);
  const [authenticated, setAuthenticated] = useState(false);

  const checkAuth = async () => {
    setCheckingAuth(true);
    try {
      const result = await api.authCheck();
      setAuthRequired(Boolean(result.auth_required));
      setAuthenticated(Boolean(result.authenticated || !result.auth_required));
    } catch {
      setAuthRequired(false);
      setAuthenticated(true);
    } finally {
      setCheckingAuth(false);
    }
  };

  useEffect(() => {
    void checkAuth();
  }, []);

  if (checkingAuth) {
    return (
      <div className="app-login-wrap">
        <Spin size="large" />
      </div>
    );
  }

  if (authRequired && !authenticated) {
    return (
      <ConfigProvider locale={zhCN}>
        <AntdApp>
          <LoginScreen onLogin={checkAuth} />
        </AntdApp>
      </ConfigProvider>
    );
  }

  return (
    <ConfigProvider
      locale={zhCN}
      theme={{
        token: {
          colorPrimary: '#1668dc',
          borderRadius: 8,
          fontFamily: '"PingFang SC", "Microsoft YaHei", "Noto Sans SC", sans-serif',
        },
      }}
    >
      <AntdApp>
        <XProvider locale={xZhCN}>
          <HashRouter>
            <Shell />
          </HashRouter>
        </XProvider>
      </AntdApp>
    </ConfigProvider>
  );
}
