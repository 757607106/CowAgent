import { Button, Drawer, Form, Input, Modal, Popconfirm, Select, Space, Table, Tag, message } from 'antd';
import { useEffect, useMemo, useState } from 'react';
import { AdvancedJsonPanel, ConsolePage, DataTableShell, PageToolbar, StatusTag } from '../components/console';
import { useRuntimeScope } from '../context/runtime';
import { api } from '../services/api';
import type { TenantItem, TenantUserItem } from '../types';

interface UserFormValues {
  tenant_id: string;
  user_id?: string;
  account?: string;
  name: string;
  role: string;
  status: string;
  password?: string;
  metadata: string;
}

interface IdentityFormValues {
  channel_type: string;
  external_user_id: string;
}

export default function TenantUsersPage() {
  const { tenantId: currentTenantId } = useRuntimeScope();
  const [loading, setLoading] = useState(false);
  const [roles, setRoles] = useState<string[]>(['owner', 'admin', 'member', 'viewer']);
  const [statuses, setStatuses] = useState<string[]>(['active', 'disabled', 'invited']);
  const [tenants, setTenants] = useState<TenantItem[]>([]);
  const [tenantId, setTenantId] = useState(currentTenantId);
  const [users, setUsers] = useState<TenantUserItem[]>([]);
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<TenantUserItem | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [identityOpen, setIdentityOpen] = useState(false);
  const [identityUser, setIdentityUser] = useState<TenantUserItem | null>(null);
  const [identities, setIdentities] = useState<any[]>([]);
  const [identitySubmitting, setIdentitySubmitting] = useState(false);

  const [form] = Form.useForm<UserFormValues>();
  const [identityForm] = Form.useForm<IdentityFormValues>();

  const tenantOptions = useMemo(
    () => tenants.map((tenant) => ({ label: tenant.name, value: tenant.tenant_id })),
    [tenants],
  );
  const tenantNameById = useMemo(
    () => new Map(tenants.map((tenant) => [tenant.tenant_id, tenant.name])),
    [tenants],
  );

  const loadMeta = async () => {
    const [metaData, tenantData] = await Promise.all([api.getTenantUserMeta(), api.listTenants()]);
    setRoles(metaData.roles || []);
    setStatuses(metaData.statuses || []);
    setTenants(tenantData.tenants || []);
  };

  const loadUsers = async () => {
    setLoading(true);
    try {
      const data = await api.listTenantUsers(tenantId);
      setUsers(data.tenant_users || []);
    } finally {
      setLoading(false);
    }
  };

  const openCreate = () => {
    setEditing(null);
    form.setFieldsValue({
      tenant_id: tenantId || currentTenantId,
      account: '',
      name: '',
      role: roles[0] || 'member',
      status: statuses[0] || 'active',
      password: '',
      metadata: '{}',
    });
    setOpen(true);
  };

  const openEdit = (row: TenantUserItem) => {
    setEditing(row);
    form.setFieldsValue({
      tenant_id: row.tenant_id,
      name: row.name,
      role: row.role,
      status: row.status,
      metadata: JSON.stringify(row.metadata || {}, null, 2),
    });
    setOpen(true);
  };

  const submit = async () => {
    const values = await form.validateFields();
    const effectiveTenantId = values.tenant_id || tenantId || currentTenantId;
    let metadata = {};
    try {
      metadata = values.metadata ? JSON.parse(values.metadata) : {};
    } catch {
      message.error('metadata 必须是合法 JSON');
      return;
    }

    setSubmitting(true);
    try {
      if (editing) {
        await api.updateTenantUser(editing.tenant_id, editing.user_id, {
          name: values.name,
          role: values.role,
          status: values.status,
          metadata,
        });
        message.success('租户成员已更新');
      } else {
        const account = (values.account || '').trim();
        const password = (values.password || '').trim();
        const data = await api.createTenantUser({
          tenant_id: effectiveTenantId,
          account: account || undefined,
          name: values.name,
          role: values.role,
          status: values.status,
          password: password || undefined,
          metadata,
        });
        message.success(password && !account
          ? `租户成员已创建，登录账号：${data.tenant_user?.user_id || ''}`
          : '租户成员已创建');
      }
      setOpen(false);
      await loadUsers();
    } finally {
      setSubmitting(false);
    }
  };

  const removeUser = async (row: TenantUserItem) => {
    await api.deleteTenantUser(row.tenant_id, row.user_id);
    message.success('租户成员已删除');
    await loadUsers();
  };

  const openIdentityDrawer = async (row: TenantUserItem) => {
    setIdentityUser(row);
    setIdentityOpen(true);
    identityForm.resetFields();
    const data = await api.listTenantIdentities(row.tenant_id, row.user_id);
    setIdentities(data.identities || []);
  };

  const bindIdentity = async () => {
    if (!identityUser) return;
    const values = await identityForm.validateFields();
    setIdentitySubmitting(true);
    try {
      await api.bindTenantIdentity({
        tenant_id: identityUser.tenant_id,
        user_id: identityUser.user_id,
        channel_type: values.channel_type,
        external_user_id: values.external_user_id,
      });
      message.success('身份映射已绑定');
      const data = await api.listTenantIdentities(identityUser.tenant_id, identityUser.user_id);
      setIdentities(data.identities || []);
      identityForm.resetFields();
    } finally {
      setIdentitySubmitting(false);
    }
  };

  const unbindIdentity = async (item: any) => {
    if (!identityUser) return;
    await api.deleteTenantIdentity(identityUser.tenant_id, item.channel_type, item.external_user_id);
    const data = await api.listTenantIdentities(identityUser.tenant_id, identityUser.user_id);
    setIdentities(data.identities || []);
    message.success('身份映射已移除');
  };

  useEffect(() => {
    void loadMeta();
  }, []);

  useEffect(() => {
    void loadUsers();
  }, [tenantId]);

  useEffect(() => {
    setTenantId(currentTenantId);
  }, [currentTenantId]);

  return (
    <ConsolePage
        title="租户成员管理"
        actions={(
          <PageToolbar>
            <Select
              allowClear
              placeholder="按租户过滤"
              className="tenant-filter"
              value={tenantId || undefined}
              onChange={(value) => setTenantId(value || '')}
              options={tenantOptions}
            />
            <Button onClick={() => void loadUsers()}>刷新</Button>
            <Button type="primary" onClick={openCreate}>新建成员</Button>
          </PageToolbar>
        )}
      >
      <DataTableShell<TenantUserItem>
        title="成员列表"
        rowKey={(row) => `${row.tenant_id}/${row.user_id}`}
        loading={loading}
        dataSource={users}
        pagination={{ pageSize: 20 }}
        columns={[
          { title: '租户', dataIndex: 'tenant_id', render: (value: string) => tenantNameById.get(value) || value },
          {
            title: '成员',
            dataIndex: 'name',
            render: (value: string, row) => (
              <span className="entity-title-cell">
                <span className="entity-title-cell-main">{value}</span>
                <span className="entity-title-cell-meta">{row.user_id}</span>
              </span>
            ),
          },
          { title: '角色', dataIndex: 'role', render: (v: string) => <Tag color="blue">{v}</Tag> },
          { title: '状态', dataIndex: 'status', render: (value: string) => <StatusTag status={value}>{value}</StatusTag> },
          {
            title: '操作',
            render: (_, row) => (
              <Space>
                <Button size="small" onClick={() => openEdit(row)}>编辑</Button>
                <Button size="small" onClick={() => void openIdentityDrawer(row)}>身份映射</Button>
                <Popconfirm title="确认删除该成员？" onConfirm={() => void removeUser(row)}>
                  <Button size="small" danger>删除</Button>
                </Popconfirm>
              </Space>
            ),
          },
        ]}
        expandable={{ expandedRowRender: (row) => <AdvancedJsonPanel title="成员 metadata" value={row.metadata || {}} defaultOpen /> }}
      />

      <Modal
        open={open}
        title={editing ? '编辑成员' : '新建成员'}
        onCancel={() => setOpen(false)}
        onOk={() => void submit()}
        confirmLoading={submitting}
      >
        <Form form={form} layout="vertical">
          {!editing && (
            <Form.Item name="account" label="登录账号" extra="可留空，系统将自动生成。">
              <Input autoComplete="off" placeholder="用于登录的唯一标识" aria-label="登录账号" />
            </Form.Item>
          )}
          <Form.Item name="name" label="姓名" rules={[{ required: true }]}>
            <Input aria-label="姓名" />
          </Form.Item>
          <Form.Item name="role" label="角色" rules={[{ required: true }]}>
            <Select aria-label="角色" options={roles.map((role) => ({ label: role, value: role }))} />
          </Form.Item>
          <Form.Item name="status" label="状态" rules={[{ required: true }]}>
            <Select aria-label="状态" options={statuses.map((status) => ({ label: status, value: status }))} />
          </Form.Item>
          <Form.Item name="metadata" label="高级配置(JSON)" htmlFor="tenant-user-metadata">
            <Input.TextArea id="tenant-user-metadata" rows={6} aria-label="高级配置 JSON" />
          </Form.Item>
          {!editing && (
            <Form.Item
              name="password"
              label="初始密码"
              htmlFor="tenant-user-password"
              dependencies={['account']}
              rules={[
                { min: 8, message: '密码至少 8 位' },
                ({ getFieldValue }) => ({
                  validator: async (_, value) => {
                    const account = String(getFieldValue('account') || '').trim();
                    if (account && !String(value || '').trim()) {
                      throw new Error('填写登录账号时必须设置初始密码');
                    }
                  },
                }),
              ]}
              extra="租户鉴权模式下使用；留空则只创建成员，不启用账号登录。"
            >
              <Input.Password id="tenant-user-password" autoComplete="new-password" placeholder="可留空" aria-label="初始密码" />
            </Form.Item>
          )}
        </Form>
      </Modal>

      <Drawer
        open={identityOpen}
        onClose={() => setIdentityOpen(false)}
        width="min(35rem, calc(100vw - 3rem))"
        title={identityUser ? `身份映射：${identityUser.name}` : '身份映射'}
      >
        <Form form={identityForm} layout="vertical">
          <Form.Item name="channel_type" label="渠道类型" rules={[{ required: true }]}>
            <Input placeholder="例如：web / weixin / feishu" aria-label="渠道类型" />
          </Form.Item>
          <Form.Item name="external_user_id" label="外部账号标识" htmlFor="tenant-user-external-id" rules={[{ required: true }]}>
            <Input id="tenant-user-external-id" aria-label="外部账号标识" />
          </Form.Item>
          <Button type="primary" loading={identitySubmitting} onClick={() => void bindIdentity()}>绑定映射</Button>
        </Form>

        <Table
          className="identity-table"
          rowKey={(row) => `${row.tenant_id}/${row.channel_type}/${row.external_user_id}`}
          pagination={false}
          dataSource={identities}
          columns={[
            { title: '渠道', dataIndex: 'channel_type' },
            { title: '外部账号标识', dataIndex: 'external_user_id' },
            {
              title: '操作',
              render: (_, row) => (
                <Popconfirm title="确认解绑该映射？" onConfirm={() => void unbindIdentity(row)}>
                  <Button size="small" danger>解绑</Button>
                </Popconfirm>
              ),
            },
          ]}
        />
      </Drawer>
    </ConsolePage>
  );
}
