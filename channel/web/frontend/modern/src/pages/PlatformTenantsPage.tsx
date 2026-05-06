import { Button, Form, Input, Modal, Popconfirm, Select, Space, message } from 'antd';
import { useEffect, useState } from 'react';
import { ConsolePage, DataTableShell, PageToolbar } from '../components/console';
import { api } from '../services/api';
import type { TenantItem } from '../types';
import {
  renderTenantMetadata,
  renderTenantStatus,
  renderTenantTitle,
  TENANT_STATUS_OPTIONS,
} from './tenantShared';

interface TenantFormValues {
  tenant_id: string;
  name: string;
  status: string;
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
    form.setFieldsValue({ tenant_id: '', name: '', status: 'active' });
    setOpen(true);
  };

  const openEdit = (row: TenantItem) => {
    setEditing(row);
    form.setFieldsValue({
      tenant_id: row.tenant_id,
      name: row.name,
      status: row.status,
    });
    setOpen(true);
  };

  const submit = async () => {
    const values = await form.validateFields();
    const metadata = editing?.metadata || {};

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
        emptyState={{
          title: '暂无租户',
          description: '创建租户后，可统一管理模型可见性、成员和运行治理。',
          action: <Button type="primary" onClick={openCreate}>新建租户</Button>,
        }}
        columns={[
          {
            title: '租户',
            dataIndex: 'name',
            render: renderTenantTitle,
          },
          { title: '状态', dataIndex: 'status', render: renderTenantStatus },
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
        expandable={{ expandedRowRender: renderTenantMetadata }}
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
            <Select aria-label="状态" options={TENANT_STATUS_OPTIONS} />
          </Form.Item>
        </Form>
      </Modal>
    </ConsolePage>
  );
}
