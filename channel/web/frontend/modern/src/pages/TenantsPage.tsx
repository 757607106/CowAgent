import { Button, Form, Input, Modal, Space, message } from 'antd';
import { useEffect, useState } from 'react';
import { AdvancedJsonPanel, ConsolePage, DataTableShell, PageToolbar, StatusTag } from '../components/console';
import { useRuntimeScope } from '../context/runtime';
import { api } from '../services/api';
import type { TenantItem } from '../types';

interface TenantFormValues {
  name: string;
  status: string;
  metadata: string;
}

export default function TenantsPage() {
  const { authUser } = useRuntimeScope();
  const canCreateTenant = !authUser;
  const [loading, setLoading] = useState(false);
  const [tenants, setTenants] = useState<TenantItem[]>([]);
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<TenantItem | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [form] = Form.useForm<TenantFormValues>();

  const load = async () => {
    setLoading(true);
    try {
      const data = await api.listTenants();
      setTenants(data.tenants || []);
    } finally {
      setLoading(false);
    }
  };

  const openCreate = () => {
    setEditing(null);
    form.setFieldsValue({ name: '', status: 'active', metadata: '{}' });
    setOpen(true);
  };

  const openEdit = (row: TenantItem) => {
    setEditing(row);
    form.setFieldsValue({
      name: row.name,
      status: row.status,
      metadata: JSON.stringify(row.metadata || {}, null, 2),
    });
    setOpen(true);
  };

  const onSubmit = async () => {
    const values = await form.validateFields();
    let metadata: Record<string, unknown> = {};
    try {
      metadata = values.metadata ? JSON.parse(values.metadata) : {};
    } catch {
      message.error('metadata 必须是合法 JSON');
      return;
    }

    setSubmitting(true);
    try {
      if (editing) {
        await api.updateTenant(editing.tenant_id, {
          name: values.name,
          status: values.status,
          metadata,
        });
        message.success('租户已更新');
      } else {
        await api.createTenant({
          name: values.name,
          status: values.status,
          metadata,
        });
        message.success('租户已创建');
      }
      setOpen(false);
      await load();
    } finally {
      setSubmitting(false);
    }
  };

  useEffect(() => {
    void load();
  }, []);

  return (
    <ConsolePage
        title="租户管理"
        actions={(
          <PageToolbar>
            <Button onClick={() => void load()}>刷新</Button>
            {canCreateTenant && <Button type="primary" onClick={openCreate}>新建租户</Button>}
          </PageToolbar>
        )}
      >
      <DataTableShell<TenantItem>
        title="租户列表"
        rowKey={(row) => row.tenant_id}
        loading={loading}
        dataSource={tenants}
        pagination={{ pageSize: 20 }}
        columns={[
          {
            title: '租户',
            dataIndex: 'name',
            render: (value: string, row) => (
              <span className="entity-title-cell">
                <span className="entity-title-cell-main">{value}</span>
                <span className="entity-title-cell-meta">{row.tenant_id}</span>
              </span>
            ),
          },
          { title: '状态', dataIndex: 'status', render: (value: string) => <StatusTag status={value}>{value}</StatusTag> },
          {
            title: '操作',
            render: (_, row) => (
              <Space>
                <Button size="small" onClick={() => openEdit(row)}>编辑</Button>
              </Space>
            ),
          },
        ]}
        expandable={{
          expandedRowRender: (row) => <AdvancedJsonPanel title="租户 metadata" value={row.metadata || {}} defaultOpen />,
        }}
      />

      <Modal
        open={open}
        title={editing ? '编辑租户' : '新建租户'}
        onCancel={() => setOpen(false)}
        onOk={() => void onSubmit()}
        confirmLoading={submitting}
        destroyOnClose
      >
        <Form form={form} layout="vertical">
          <Form.Item name="name" label="名称" rules={[{ required: true }]}>
            <Input aria-label="名称" />
          </Form.Item>
          <Form.Item name="status" label="状态" rules={[{ required: true }]}>
            <Input aria-label="状态" />
          </Form.Item>
          <Form.Item name="metadata" label="高级配置(JSON)" htmlFor="tenant-metadata">
            <Input.TextArea id="tenant-metadata" rows={6} aria-label="高级配置 JSON" />
          </Form.Item>
        </Form>
      </Modal>
    </ConsolePage>
  );
}
