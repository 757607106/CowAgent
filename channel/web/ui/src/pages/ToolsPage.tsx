import { Button, Card, Space, Table } from 'antd';
import { useEffect, useState } from 'react';
import { PageTitle } from '../components/PageTitle';
import { api } from '../services/api';
import type { ToolItem } from '../types';

export default function ToolsPage() {
  const [loading, setLoading] = useState(false);
  const [tools, setTools] = useState<ToolItem[]>([]);

  const load = async () => {
    setLoading(true);
    try {
      const data = await api.listTools();
      setTools(data.tools || []);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, []);

  return (
    <Card>
      <PageTitle
        title="工具管理"
        description="查看当前系统可用的内置工具。"
        extra={<Button onClick={() => void load()}>刷新</Button>}
      />
      <Table<ToolItem>
        rowKey="name"
        loading={loading}
        dataSource={tools}
        pagination={false}
        columns={[
          { title: '工具名', dataIndex: 'name' },
          { title: '描述', dataIndex: 'description', render: (v: string) => v || '-' },
        ]}
      />
      <Space style={{ marginTop: 12 }}>
        <span>共 {tools.length} 个工具</span>
      </Space>
    </Card>
  );
}
