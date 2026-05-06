import { Button, Form, Input, Modal, Space, message } from 'antd';
import { useEffect, useState } from 'react';
import { ConsolePage, DataTableShell, PageToolbar } from '../components/console';
import { useRuntimeScope } from '../context/runtime';
import { api } from '../services/api';
import type { TenantItem } from '../types';
import {
  renderTenantMetadata,
  renderTenantStatus,
  renderTenantTitle,
} from './tenantShared';

interface TenantFormValues {
  name: string;
  status: string;
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
    form.setFieldsValue({ name: '', status: 'active' });
    setOpen(true);
  };

  const openEdit = (row: TenantItem) => {
    setEditing(row);
    form.setFieldsValue({
      name: row.name,
      status: row.status,
    });
    setOpen(true);
  };

  const onSubmit = async () => {
    const values = await form.validateFields();
    const metadata = editing?.metadata || {};

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
        emptyState={{
          title: '暂无租户',
          description: '租户信息会在这里展示，用于区分成员、模型和渠道资源边界。',
          action: canCreateTenant ? <Button type="primary" onClick={openCreate}>新建租户</Button> : undefined,
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
              </Space>
            ),
          },
        ]}
        expandable={{
          expandedRowRender: renderTenantMetadata,
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
        </Form>
      </Modal>
    </ConsolePage>
  );
}
