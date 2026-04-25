import { Button, Form, Input, Modal, Popconfirm, Select, Space, message } from 'antd';
import { useEffect, useState } from 'react';
import { AdvancedJsonPanel, ConsolePage, DataTableShell, PageToolbar, StatusTag } from '../components/console';
import { api } from '../services/api';
import type { TenantItem } from '../types';

interface TenantFormValues {
  tenant_id: string;
  name: string;
  status: string;
  metadata: string;
}

export default function PlatformTenantsPage() {
  const [loading, setLoading] = useState(false);
  const [tenants, setTenants] = useState<TenantItem[]>([]);
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<TenantItem | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [form] = Form.useForm<TenantFormValues>();

  const load = async () => {
    setLoading(true);
    try {
      const data = await api.listPlatformTenants();
      setTenants(data.tenants || []);
    } finally {
      setLoading(false);
    }
  };

  const openCreate = () => {
    setEditing(null);
    form.setFieldsValue({ tenant_id: '', name: '', status: 'active', metadata: '{}' });
    setOpen(true);
  };

  const openEdit = (row: TenantItem) => {
    setEditing(row);
    form.setFieldsValue({
      tenant_id: row.tenant_id,
      name: row.name,
      status: row.status,
      metadata: JSON.stringify(row.metadata || {}, null, 2),
    });
    setOpen(true);
  };

  const parseMetadata = (text: string) => {
    try {
      return text ? JSON.parse(text) : {};
    } catch {
      message.error('metadata 必须是合法 JSON');
      return null;
    }
  };

  const submit = async () => {
    const values = await form.validateFields();
    const metadata = parseMetadata(values.metadata);
    if (metadata === null) return;

    setSubmitting(true);
    try {
      if (editing) {
        await api.updatePlatformTenant(editing.tenant_id, {
          name: values.name,
          status: values.status,
          metadata,
        });
        message.success('租户已更新');
      } else {
        await api.createPlatformTenant({
          tenant_id: values.tenant_id,
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

  const remove = async (row: TenantItem) => {
    await api.deletePlatformTenant(row.tenant_id);
    message.success('租户已删除');
    await load();
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
            <Button type="primary" onClick={openCreate}>新建租户</Button>
          </PageToolbar>
        )}
      >
      <DataTableShell<TenantItem>
        title="平台租户"
        rowKey="tenant_id"
        loading={loading}
        dataSource={tenants}
        pagination={{ pageSize: 12 }}
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
                <Popconfirm title="确认删除该租户？" onConfirm={() => void remove(row)}>
                  <Button size="small" danger disabled={row.tenant_id === 'default'}>删除</Button>
                </Popconfirm>
              </Space>
            ),
          },
        ]}
        expandable={{ expandedRowRender: (row) => <AdvancedJsonPanel title="租户 metadata" value={row.metadata || {}} defaultOpen /> }}
      />

      <Modal
        open={open}
        title={editing ? '编辑租户' : '新建租户'}
        onCancel={() => setOpen(false)}
        onOk={() => void submit()}
        confirmLoading={submitting}
        destroyOnClose
      >
        <Form form={form} layout="vertical">
          <Form.Item name="tenant_id" label="租户 ID">
            <Input disabled={Boolean(editing)} placeholder="留空则自动生成" aria-label="租户 ID" />
          </Form.Item>
          <Form.Item name="name" label="名称" rules={[{ required: true }]}>
            <Input aria-label="名称" />
          </Form.Item>
          <Form.Item name="status" label="状态" rules={[{ required: true }]}>
            <Select aria-label="状态" options={[
              { label: 'active', value: 'active' },
              { label: 'disabled', value: 'disabled' },
              { label: 'deleted', value: 'deleted' },
            ]} />
          </Form.Item>
          <Form.Item name="metadata" label="高级配置(JSON)" htmlFor="platform-tenant-metadata">
            <Input.TextArea id="platform-tenant-metadata" rows={6} aria-label="高级配置 JSON" />
          </Form.Item>
        </Form>
      </Modal>
    </ConsolePage>
  );
}
