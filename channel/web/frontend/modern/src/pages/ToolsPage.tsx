import { Button } from 'antd';
import { useEffect, useState } from 'react';
import { ConsolePage, DataTableShell, PageToolbar } from '../components/console';
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
    <ConsolePage
        title="工具管理"
        actions={<PageToolbar><Button onClick={() => void load()}>刷新</Button></PageToolbar>}
      >
      <DataTableShell<ToolItem>
        title={`工具列表：${tools.length}`}
        rowKey="name"
        loading={loading}
        dataSource={tools}
        pagination={false}
        columns={[
          { title: '工具名', dataIndex: 'name' },
          { title: '描述', dataIndex: 'description', render: (v: string) => v || '-' },
        ]}
      />
    </ConsolePage>
  );
}
