import { Button, Card, Form, Input, Modal, Popconfirm, Space, Table, Tag, message } from 'antd';
import { useEffect, useState } from 'react';
import { JsonBlock } from '../components/JsonBlock';
import { PageTitle } from '../components/PageTitle';
import { api } from '../services/api';
import type { TenantItem } from '../types';

interface TenantFormValues {
  tenant_id: string;
  name: string;
  status: string;
  metadata: string;
}

export default function TenantsPage() {
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

  useEffect(() => {
    void load();
  }, []);

  return (
    <Card>
      <PageTitle
        title="租户管理"
        description="维护多租户基础信息。"
        extra={(
          <Space>
            <Button onClick={() => void load()}>刷新</Button>
            <Button type="primary" onClick={openCreate}>新建租户</Button>
          </Space>
        )}
      />
      <Table<TenantItem>
        rowKey={(row) => row.tenant_id}
        loading={loading}
        dataSource={tenants}
        pagination={{ pageSize: 20 }}
        columns={[
          { title: '租户ID', dataIndex: 'tenant_id' },
          { title: '名称', dataIndex: 'name' },
          { title: '状态', dataIndex: 'status', render: (v: string) => (v === 'active' ? <Tag color="green">active</Tag> : <Tag>{v}</Tag>) },
          {
            title: '操作',
            render: (_, row) => (
              <Space>
                <Button size="small" onClick={() => openEdit(row)}>编辑</Button>
                <Popconfirm title="当前后端未提供删除租户接口，仅支持编辑。" showCancel={false}>
                  <Button size="small" danger disabled>删除</Button>
                </Popconfirm>
              </Space>
            ),
          },
        ]}
        expandable={{
          expandedRowRender: (row) => <JsonBlock value={row.metadata || {}} />,
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
          <Form.Item name="tenant_id" label="租户ID" rules={[{ required: true }]}>
            <Input disabled={Boolean(editing)} />
          </Form.Item>
          <Form.Item name="name" label="名称" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="status" label="状态" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="metadata" label="Metadata(JSON)">
            <Input.TextArea rows={6} />
          </Form.Item>
        </Form>
      </Modal>
    </Card>
  );
}
