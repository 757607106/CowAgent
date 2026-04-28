import {
  LogoutOutlined,
  MenuOutlined,
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
import { getFlatMenuItemsForRole, getMenuItemsForRole } from './app/navigation';
import { appTheme } from './app/theme';
import { api } from './services/api';
import type { AuthUser, RuntimeScope } from './types';

const { Sider, Content } = Layout;

const AGENT_KEY = 'cowagent_runtime_agent_id';
const BINDING_KEY = 'cowagent_runtime_binding_id';

const DEFAULT_AGENT_OPTION: RuntimeAgentOption = { label: DEFAULT_AGENT_NAME, value: DEFAULT_AGENT_ID };

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
  const isPlatformAdmin = authUser?.principal_type === 'platform';
  const teamLabel = isPlatformAdmin ? '平台管理' : authUser?.tenant_name || '当前团队';
  const accountLabel = authUser?.account || authUser?.user_name || '已登录';

  return (
    <>
      <div className="app-logo">CowAgent 2.0.6</div>
      {authUser && (
        <div className="app-tenant-session">
          <div className="app-tenant-session-meta">
            <Typography.Text className="app-tenant-name" title={teamLabel}>
              {teamLabel}
            </Typography.Text>
            <Typography.Text className="app-tenant-user" title={accountLabel}>
              {accountLabel}
            </Typography.Text>
          </div>
        </div>
      )}
      <Menu
        mode="inline"
        selectedKeys={selectedMenu}
        items={getMenuItemsForRole(isPlatformAdmin)}
        onClick={({ key }) => onMenuClick(String(key))}
        className="app-nav-menu"
      />
      {authUser && (
        <div className="app-sidebar-footer">
          <Button
            block
            size="middle"
            icon={<LogoutOutlined />}
            onClick={() => void onLogout()}
          >
            退出登录
          </Button>
        </div>
      )}
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
        <Typography.Title level={3} className="app-login-title">CowAgent 控制台</Typography.Title>
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
                    <Input autoComplete="username" aria-label="平台账号" />
                  </Form.Item>
                  <Form.Item name="name" label="姓名">
                    <Input autoComplete="name" aria-label="姓名" />
                  </Form.Item>
                  <Form.Item name="password" label="密码" htmlFor="platform-password" rules={[{ required: true, min: 8, message: '密码至少 8 位' }]}>
                    <Input.Password id="platform-password" autoComplete="new-password" aria-label="密码" />
                  </Form.Item>
                  <Form.Item name="confirm_password" label="确认密码" htmlFor="platform-confirm-password" rules={[{ required: true, message: '请再次输入密码' }]}>
                    <Input.Password id="platform-confirm-password" autoComplete="new-password" aria-label="确认密码" onPressEnter={() => void submitPlatformRegister()} />
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
                      <Input autoComplete="username" aria-label="登录账号" onPressEnter={() => void submitLogin()} />
                    </Form.Item>
                  )}
                  <Form.Item name="password" label="密码" htmlFor="login-password" rules={[{ required: true, message: '请输入密码' }]}>
                    <Input.Password id="login-password" autoComplete="current-password" aria-label="密码" onPressEnter={() => void submitLogin()} />
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
                    <Input autoComplete="organization" aria-label="团队名称" />
                  </Form.Item>
                  <Form.Item name="account" label="登录账号" rules={[{ required: true, message: '请输入登录账号' }]}>
                    <Input autoComplete="username" aria-label="登录账号" />
                  </Form.Item>
                  <Form.Item name="user_name" label="你的姓名">
                    <Input autoComplete="name" aria-label="你的姓名" />
                  </Form.Item>
                  <Form.Item name="password" label="密码" htmlFor="register-password" rules={[{ required: true, min: 8, message: '密码至少 8 位' }]}>
                    <Input.Password id="register-password" autoComplete="new-password" aria-label="密码" />
                  </Form.Item>
                  <Form.Item name="confirm_password" label="确认密码" htmlFor="register-confirm-password" rules={[{ required: true, message: '请再次输入密码' }]}>
                    <Input.Password id="register-confirm-password" autoComplete="new-password" aria-label="确认密码" onPressEnter={() => void submitRegister()} />
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
  const flatMenuItems = useMemo(() => getFlatMenuItemsForRole(isPlatformAdmin), [isPlatformAdmin]);
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
    const target = flatMenuItems.find((item) => location.pathname.startsWith(item.key));
    return target ? [target.key] : [isPlatformAdmin ? '/platform/models' : '/chat'];
  }, [flatMenuItems, isPlatformAdmin, location.pathname]);

  const currentMenuLabel = useMemo(() => {
    const selectedKey = selectedMenu[0] || '/chat';
    return flatMenuItems.find((item) => item.key === selectedKey)?.label || '控制台';
  }, [flatMenuItems, selectedMenu]);

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
        <Sider width="var(--sidebar-width)" theme="light" className="app-sider">
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
              <Route path="/platform/logs" element={isPlatformAdmin ? <LogsPage /> : <Navigate to="/chat" replace />} />
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
              <Route path="/logs" element={<Navigate to={isPlatformAdmin ? '/platform/logs' : '/chat'} replace />} />
              <Route path="*" element={<Navigate to={isPlatformAdmin ? '/platform/models' : '/chat'} replace />} />
            </Routes>
          </Content>
        </Layout>
        <Drawer
          className="app-mobile-drawer"
          title="CowAgent 2.0.6"
          placement="left"
          width="17.5rem"
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
