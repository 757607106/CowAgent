import {
  ApiOutlined,
  ApartmentOutlined,
  AppstoreOutlined,
  BarChartOutlined,
  BuildOutlined,
  ClusterOutlined,
  FileTextOutlined,
  LogoutOutlined,
  MenuOutlined,
  MessageOutlined,
  ScheduleOutlined,
  SettingOutlined,
  TeamOutlined,
} from '@ant-design/icons';
import { App as AntdApp, Button, ConfigProvider, Drawer, Form, Input, Layout, Menu, Spin, Tabs, Tag, Typography, message } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { HashRouter, Navigate, Route, Routes, useLocation, useNavigate } from 'react-router-dom';
import { XProvider } from '@ant-design/x';
import xZhCN from '@ant-design/x/locale/zh_CN';
import ChatPage from './pages/ChatPage';
import AgentsPage from './pages/AgentsPage';
import ChannelAccessPage from './pages/ChannelAccessPage';
import SkillsPage from './pages/SkillsPage';
import McpPage from './pages/McpPage';
import TenantsPage from './pages/TenantsPage';
import TenantUsersPage from './pages/TenantUsersPage';
import TenantModelsPage from './pages/TenantModelsPage';
import PlatformModelsPage from './pages/PlatformModelsPage';
import PlatformTenantsPage from './pages/PlatformTenantsPage';
import TasksPage from './pages/TasksPage';
import LogsPage from './pages/LogsPage';
import UsagePage from './pages/UsagePage';
import { DEFAULT_AGENT_ID, DEFAULT_AGENT_NAME, WORKSPACE_AGENT_VALUE, displayAgentName, type RuntimeAgentOption, RuntimeContext } from './context/runtime';
import { api } from './services/api';
import type { AuthUser, RuntimeScope } from './types';

const { Sider, Content } = Layout;

const AGENT_KEY = 'cowagent_runtime_agent_id';
const BINDING_KEY = 'cowagent_runtime_binding_id';

const DEFAULT_AGENT_OPTION: RuntimeAgentOption = { label: DEFAULT_AGENT_NAME, value: DEFAULT_AGENT_ID };

const appTheme = {
  token: {
    colorPrimary: '#1a6ff5',
    colorSuccess: '#10b981',
    colorWarning: '#f59e0b',
    colorError: '#ef4444',
    colorInfo: '#1a6ff5',
    borderRadius: 8,
    borderRadiusLG: 12,
    borderRadiusSM: 6,
    fontFamily: '"PingFang SC", "Microsoft YaHei", "Noto Sans SC", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
    fontSize: 14,
    fontSizeLG: 16,
    fontSizeSM: 12,
    lineHeight: 1.5,
    controlHeight: 34,
    controlHeightLG: 40,
    controlHeightSM: 28,
    paddingContentHorizontal: 16,
    paddingContentVertical: 12,
    colorBgContainer: '#ffffff',
    colorBgElevated: '#ffffff',
    colorBgLayout: '#f5f7fa',
    colorBorder: '#e4e8ee',
    colorBorderSecondary: '#eef1f6',
    colorText: '#1f2430',
    colorTextSecondary: '#4b5362',
    colorTextTertiary: '#8891a0',
    boxShadow: '0 1px 2px 0 rgba(0, 0, 0, 0.03), 0 1px 3px 0 rgba(0, 0, 0, 0.04)',
    boxShadowSecondary: '0 4px 6px -1px rgba(0, 0, 0, 0.04), 0 2px 4px -2px rgba(0, 0, 0, 0.04)',
    wireframe: false,
  },
  components: {
    Menu: {
      itemBorderRadius: 8,
      itemHeight: 36,
      itemMarginInline: 8,
      itemHoverBg: '#f5f7fa',
      itemSelectedBg: '#eff4ff',
      itemSelectedColor: '#1a6ff5',
      itemActiveBg: '#eff4ff',
      iconSize: 18,
      collapsedIconSize: 18,
    },
    Card: {
      paddingLG: 20,
      borderRadiusLG: 12,
    },
    Button: {
      borderRadius: 8,
      borderRadiusLG: 10,
      borderRadiusSM: 6,
      controlHeight: 34,
      controlHeightLG: 40,
      controlHeightSM: 28,
      fontWeight: 500,
    },
    Tag: {
      borderRadiusSM: 6,
      fontSizeSM: 11,
      lineHeightSM: 1.4,
    },
    Table: {
      borderRadius: 8,
      borderColor: '#e4e8ee',
      headerBg: '#f8fafc',
      headerColor: '#4b5362',
      rowHoverBg: '#f5f7fa',
    },
    Input: {
      borderRadius: 8,
      borderRadiusLG: 10,
      borderRadiusSM: 6,
    },
    Select: {
      borderRadius: 8,
      borderRadiusLG: 10,
      borderRadiusSM: 6,
    },
    Modal: {
      borderRadiusLG: 16,
      titleFontSize: 18,
    },
    Drawer: {
      borderRadiusLG: 0,
    },
    Collapse: {
      borderRadiusLG: 12,
      contentPadding: '16px 20px',
      headerPadding: '14px 20px',
    },
    Form: {
      itemMarginBottom: 16,
      labelFontSize: 13,
    },
    Switch: {
      trackHeight: 22,
      trackMinWidth: 40,
      handleSize: 18,
    },
    Tooltip: {
      borderRadius: 8,
    },
    Popover: {
      borderRadius: 12,
    },
  },
};

const tenantMenuItems = [
  { key: '/chat', icon: <MessageOutlined />, label: '对话' },
  { key: '/tenant-models', icon: <SettingOutlined />, label: '租户模型' },
  { key: '/agents', icon: <AppstoreOutlined />, label: 'AI 员工' },
  { key: '/skills', icon: <BuildOutlined />, label: '技能' },
  { key: '/mcp', icon: <ApiOutlined />, label: 'MCP' },
  { key: '/channels', icon: <ClusterOutlined />, label: '渠道接入' },
  { key: '/usage', icon: <BarChartOutlined />, label: '用量' },
  { key: '/tenant-users', icon: <TeamOutlined />, label: '租户成员' },
  { key: '/tasks', icon: <ScheduleOutlined />, label: '任务' },
  { key: '/logs', icon: <FileTextOutlined />, label: '日志' },
];

const platformMenuItems = [
  { key: '/platform/models', icon: <SettingOutlined />, label: '平台模型' },
  { key: '/platform/tenants', icon: <ApartmentOutlined />, label: '租户管理' },
];

interface AuthCheckState {
  authRequired: boolean;
  authenticated: boolean;
  bootstrapRequired: boolean;
  platformBootstrapRequired: boolean;
  authMode: string;
  user: AuthUser | null;
}

function normalizeRuntimeAgentId(value?: string | null): string {
  if (!value || value === WORKSPACE_AGENT_VALUE) return DEFAULT_AGENT_ID;
  return value;
}

function SidebarContent({
  authUser,
  selectedMenu,
  onMenuClick,
  onLogout,
}: {
  authUser: AuthUser | null;
  selectedMenu: string[];
  onMenuClick: (key: string) => void;
  onLogout: () => Promise<void>;
}) {
  return (
    <>
      <div className="app-logo">CowAgent 2.0.6</div>
      {authUser && (
        <div className="app-tenant-session">
          <div className="app-tenant-session-meta">
            <Tag color={authUser.principal_type === 'platform' ? 'purple' : 'blue'}>
              {authUser.principal_type === 'platform' ? '平台超管' : authUser.tenant_name || '当前团队'}
            </Tag>
            <Typography.Text className="app-tenant-user">
              {authUser.user_name || authUser.account || '已登录'}
            </Typography.Text>
          </div>
          <Button
            size="small"
            icon={<LogoutOutlined />}
            onClick={() => void onLogout()}
            title="退出登录"
          />
        </div>
      )}
      <Menu
        mode="inline"
        selectedKeys={selectedMenu}
        items={authUser?.principal_type === 'platform' ? platformMenuItems : tenantMenuItems}
        onClick={({ key }) => onMenuClick(String(key))}
        className="app-nav-menu"
      />
    </>
  );
}

function LoginScreen({
  onLogin,
  bootstrapRequired,
  platformBootstrapRequired,
  authMode,
}: {
  onLogin: () => Promise<void>;
  bootstrapRequired: boolean;
  platformBootstrapRequired: boolean;
  authMode: string;
}) {
  const [loginForm] = Form.useForm<{ account: string; password: string }>();
  const [registerForm] = Form.useForm<{
    tenant_name: string;
    account: string;
    user_name: string;
    password: string;
    confirm_password: string;
  }>();
  const [platformForm] = Form.useForm<{
    account: string;
    name: string;
    password: string;
    confirm_password: string;
  }>();
  const [activeKey, setActiveKey] = useState(platformBootstrapRequired ? 'platform' : (bootstrapRequired ? 'register' : 'login'));
  const [submitting, setSubmitting] = useState(false);

  const submitLogin = async () => {
    const values = await loginForm.validateFields();
    setSubmitting(true);
    try {
      await api.login(
        authMode === 'tenant'
          ? { account: values.account, password: values.password }
          : { password: values.password },
      );
      await onLogin();
      message.success('登录成功');
    } catch (error) {
      message.error(error instanceof Error ? error.message : '登录失败');
    } finally {
      setSubmitting(false);
    }
  };

  const submitRegister = async () => {
    const values = await registerForm.validateFields();
    if (values.password !== values.confirm_password) {
      message.error('两次输入的密码不一致');
      return;
    }
    setSubmitting(true);
    try {
      await api.registerTenant({
        tenant_name: values.tenant_name,
        account: values.account,
        user_name: values.user_name,
        password: values.password,
      });
      await onLogin();
      message.success('团队已创建');
    } catch (error) {
      message.error(error instanceof Error ? error.message : '注册失败');
    } finally {
      setSubmitting(false);
    }
  };

  const submitPlatformRegister = async () => {
    const values = await platformForm.validateFields();
    if (values.password !== values.confirm_password) {
      message.error('两次输入的密码不一致');
      return;
    }
    setSubmitting(true);
    try {
      await api.registerPlatformAdmin({
        account: values.account,
        name: values.name,
        password: values.password,
      });
      await onLogin();
      message.success('平台管理员已创建');
    } catch (error) {
      message.error(error instanceof Error ? error.message : '创建失败');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="app-login-wrap">
      <div className="app-login-panel">
        <Typography.Title level={3} style={{ marginTop: 0 }}>CowAgent 控制台</Typography.Title>
        <Tabs
          activeKey={activeKey}
          onChange={setActiveKey}
          items={[
            ...(platformBootstrapRequired ? [{
              key: 'platform',
              label: '平台初始化',
              children: (
                <Form form={platformForm} layout="vertical">
                  <Form.Item name="account" label="平台账号" rules={[{ required: true, message: '请输入平台账号' }]}>
                    <Input autoComplete="username" />
                  </Form.Item>
                  <Form.Item name="name" label="姓名">
                    <Input autoComplete="name" />
                  </Form.Item>
                  <Form.Item name="password" label="密码" rules={[{ required: true, min: 8, message: '密码至少 8 位' }]}>
                    <Input.Password autoComplete="new-password" />
                  </Form.Item>
                  <Form.Item name="confirm_password" label="确认密码" rules={[{ required: true, message: '请再次输入密码' }]}>
                    <Input.Password autoComplete="new-password" onPressEnter={() => void submitPlatformRegister()} />
                  </Form.Item>
                  <Button type="primary" block loading={submitting} onClick={() => void submitPlatformRegister()}>创建平台超管</Button>
                </Form>
              ),
            }] : []),
            {
              key: 'login',
              label: '登录',
              children: (
                <Form form={loginForm} layout="vertical">
                  {authMode === 'tenant' && (
                    <Form.Item name="account" label="登录账号" rules={[{ required: true, message: '请输入登录账号' }]}>
                      <Input autoComplete="username" onPressEnter={() => void submitLogin()} />
                    </Form.Item>
                  )}
                  <Form.Item name="password" label="密码" rules={[{ required: true, message: '请输入密码' }]}>
                    <Input.Password autoComplete="current-password" onPressEnter={() => void submitLogin()} />
                  </Form.Item>
                  <Button type="primary" block loading={submitting} onClick={() => void submitLogin()}>登录</Button>
                </Form>
              ),
            },
            ...(authMode === 'tenant' ? [{
              key: 'register',
              label: '注册租户',
              children: (
                <Form form={registerForm} layout="vertical">
                  <Form.Item name="tenant_name" label="团队名称" rules={[{ required: true, message: '请输入团队名称' }]}>
                    <Input autoComplete="organization" />
                  </Form.Item>
                  <Form.Item name="account" label="登录账号" rules={[{ required: true, message: '请输入登录账号' }]}>
                    <Input autoComplete="username" />
                  </Form.Item>
                  <Form.Item name="user_name" label="你的姓名">
                    <Input autoComplete="name" />
                  </Form.Item>
                  <Form.Item name="password" label="密码" rules={[{ required: true, min: 8, message: '密码至少 8 位' }]}>
                    <Input.Password autoComplete="new-password" />
                  </Form.Item>
                  <Form.Item name="confirm_password" label="确认密码" rules={[{ required: true, message: '请再次输入密码' }]}>
                    <Input.Password autoComplete="new-password" onPressEnter={() => void submitRegister()} />
                  </Form.Item>
                  <Button type="primary" block loading={submitting} onClick={() => void submitRegister()}>注册并登录</Button>
                </Form>
              ),
            }] : []),
          ]}
        />
      </div>
    </div>
  );
}

function Shell({ authUser, onLogout }: { authUser: AuthUser | null; onLogout: () => Promise<void> }) {
  const navigate = useNavigate();
  const location = useLocation();
  const tenantId = authUser?.tenant_id || 'default';
  const isPlatformAdmin = authUser?.principal_type === 'platform';
  const activeMenuItems = isPlatformAdmin ? platformMenuItems : tenantMenuItems;
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const [scope, setScope] = useState<RuntimeScope>({
    tenantId,
    agentId: normalizeRuntimeAgentId(localStorage.getItem(AGENT_KEY)),
    bindingId: '',
  });
  const [agentOptions, setAgentOptions] = useState<RuntimeAgentOption[]>([]);

  const loadRuntimeOptions = useCallback(async () => {
    if (isPlatformAdmin) {
      setAgentOptions([]);
      return;
    }
    const agentData = await api.listAgentsSimple();
    const options = (agentData.agents || []).map((agent) => ({
      label: displayAgentName(agent.agent_id, agent.name),
      value: agent.agent_id,
    }));
    setAgentOptions(options.some((item) => item.value === DEFAULT_AGENT_ID)
      ? options
      : [DEFAULT_AGENT_OPTION, ...options]);
  }, [isPlatformAdmin]);

  useEffect(() => {
    localStorage.removeItem(BINDING_KEY);
    void loadRuntimeOptions();
  }, [loadRuntimeOptions]);

  const setAgentScope = useCallback((value?: string) => {
    const resolvedAgentId = normalizeRuntimeAgentId(value);
    const next = { tenantId, agentId: resolvedAgentId, bindingId: '' };
    setScope(next);
    localStorage.removeItem(BINDING_KEY);
    localStorage.setItem(AGENT_KEY, next.agentId);
  }, [tenantId]);

  useEffect(() => {
    setScope((current) => ({ ...current, tenantId }));
  }, [tenantId]);

  const selectedMenu = useMemo(() => {
    if (location.pathname.startsWith('/bindings')) return ['/channels'];
    const target = activeMenuItems.find((item) => location.pathname.startsWith(item.key));
    return target ? [target.key] : [isPlatformAdmin ? '/platform/models' : '/chat'];
  }, [activeMenuItems, isPlatformAdmin, location.pathname]);

  const currentMenuLabel = useMemo(() => {
    const selectedKey = selectedMenu[0] || '/chat';
    return activeMenuItems.find((item) => item.key === selectedKey)?.label || '控制台';
  }, [activeMenuItems, selectedMenu]);

  const handleMenuClick = useCallback((key: string) => {
    navigate(key);
    setMobileMenuOpen(false);
  }, [navigate]);

  return (
    <RuntimeContext.Provider
      value={{
        tenantId,
        authUser,
        scope,
        setScope,
        agentOptions,
        refreshAgentOptions: loadRuntimeOptions,
        setAgentScope,
        logout: onLogout,
      }}
    >
      <Layout className="app-layout" hasSider>
        <Sider width={220} theme="light" className="app-sider">
          <SidebarContent
            authUser={authUser}
            selectedMenu={selectedMenu}
            onMenuClick={handleMenuClick}
            onLogout={onLogout}
          />
        </Sider>
        <Layout className="app-main-layout">
          <div className="app-mobile-header">
            <Button
              type="text"
              shape="circle"
              icon={<MenuOutlined />}
              aria-label="打开导航"
              onClick={() => setMobileMenuOpen(true)}
            />
            <div className="app-mobile-title">
              <Typography.Text strong>CowAgent</Typography.Text>
              <Typography.Text type="secondary">{currentMenuLabel}</Typography.Text>
            </div>
            {authUser ? <Tag color={isPlatformAdmin ? 'purple' : 'blue'}>{isPlatformAdmin ? '平台超管' : authUser.tenant_name || '当前团队'}</Tag> : null}
          </div>
          <Content className="app-content">
            <Routes>
              <Route path="/" element={<Navigate to={isPlatformAdmin ? '/platform/models' : '/chat'} replace />} />
              <Route path="/platform/models" element={isPlatformAdmin ? <PlatformModelsPage /> : <Navigate to="/chat" replace />} />
              <Route path="/platform/tenants" element={isPlatformAdmin ? <PlatformTenantsPage /> : <Navigate to="/chat" replace />} />
              <Route path="/chat" element={isPlatformAdmin ? <Navigate to="/platform/models" replace /> : <ChatPage />} />
              <Route path="/config" element={<Navigate to={isPlatformAdmin ? '/platform/models' : '/tenant-models'} replace />} />
              <Route path="/tenant-models" element={isPlatformAdmin ? <Navigate to="/platform/models" replace /> : <TenantModelsPage />} />
              <Route path="/agents" element={isPlatformAdmin ? <Navigate to="/platform/models" replace /> : <AgentsPage />} />
              <Route path="/tools" element={<Navigate to="/agents" replace />} />
              <Route path="/skills" element={isPlatformAdmin ? <Navigate to="/platform/models" replace /> : <SkillsPage />} />
              <Route path="/mcp" element={isPlatformAdmin ? <Navigate to="/platform/models" replace /> : <McpPage />} />
              <Route path="/memory" element={<Navigate to="/agents" replace />} />
              <Route path="/knowledge" element={<Navigate to="/agents" replace />} />
              <Route path="/bindings" element={isPlatformAdmin ? <Navigate to="/platform/models" replace /> : <ChannelAccessPage defaultTab="bindings" />} />
              <Route path="/channels" element={isPlatformAdmin ? <Navigate to="/platform/models" replace /> : <ChannelAccessPage defaultTab="channels" />} />
              <Route path="/usage" element={isPlatformAdmin ? <Navigate to="/platform/models" replace /> : <UsagePage />} />
              <Route path="/tenants" element={isPlatformAdmin ? <Navigate to="/platform/models" replace /> : <TenantsPage />} />
              <Route path="/tenant-users" element={isPlatformAdmin ? <Navigate to="/platform/models" replace /> : <TenantUsersPage />} />
              <Route path="/tasks" element={isPlatformAdmin ? <Navigate to="/platform/models" replace /> : <TasksPage />} />
              <Route path="/logs" element={isPlatformAdmin ? <Navigate to="/platform/models" replace /> : <LogsPage />} />
              <Route path="*" element={<Navigate to={isPlatformAdmin ? '/platform/models' : '/chat'} replace />} />
            </Routes>
          </Content>
        </Layout>
        <Drawer
          className="app-mobile-drawer"
          title="CowAgent 2.0.6"
          placement="left"
          width={280}
          open={mobileMenuOpen}
          onClose={() => setMobileMenuOpen(false)}
        >
          <SidebarContent
            authUser={authUser}
            selectedMenu={selectedMenu}
            onMenuClick={handleMenuClick}
            onLogout={onLogout}
          />
        </Drawer>
      </Layout>
    </RuntimeContext.Provider>
  );
}

export default function App() {
  const [checkingAuth, setCheckingAuth] = useState(true);
  const [authState, setAuthState] = useState<AuthCheckState>({
    authRequired: false,
    authenticated: false,
    bootstrapRequired: false,
    platformBootstrapRequired: false,
    authMode: 'none',
    user: null,
  });

  const checkAuth = async () => {
    setCheckingAuth(true);
    try {
      const result = await api.authCheck();
      setAuthState({
        authRequired: Boolean(result.auth_required),
        authenticated: Boolean(result.authenticated || !result.auth_required),
        bootstrapRequired: Boolean(result.bootstrap_required),
        platformBootstrapRequired: Boolean(result.platform_bootstrap_required),
        authMode: result.auth_mode || 'none',
        user: result.user || null,
      });
    } catch {
      setAuthState({
        authRequired: false,
        authenticated: true,
        bootstrapRequired: false,
        platformBootstrapRequired: false,
        authMode: 'none',
        user: null,
      });
    } finally {
      setCheckingAuth(false);
    }
  };

  const logout = async () => {
    await api.logout();
    await checkAuth();
    message.success('已退出登录');
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

  if (authState.authRequired && !authState.authenticated) {
    return (
      <ConfigProvider locale={zhCN} theme={appTheme}>
        <AntdApp>
          <LoginScreen
            onLogin={checkAuth}
            bootstrapRequired={authState.bootstrapRequired}
            platformBootstrapRequired={authState.platformBootstrapRequired}
            authMode={authState.authMode}
          />
        </AntdApp>
      </ConfigProvider>
    );
  }

  return (
    <ConfigProvider
      locale={zhCN}
      theme={appTheme}
    >
      <AntdApp>
        <XProvider locale={xZhCN}>
          <HashRouter>
            <Shell authUser={authState.user} onLogout={logout} />
          </HashRouter>
        </XProvider>
      </AntdApp>
    </ConfigProvider>
  );
}
