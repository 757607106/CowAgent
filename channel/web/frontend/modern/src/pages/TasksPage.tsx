import { Button } from 'antd';
import { useEffect, useState } from 'react';
import { useRuntimeScope } from '../context/runtime';
import { AdvancedJsonPanel, ConsolePage, DataTableShell, PageToolbar, StatusTag } from '../components/console';
import { api } from '../services/api';

export default function TasksPage() {
  const { scope } = useRuntimeScope();
  const [loading, setLoading] = useState(false);
  const [tasks, setTasks] = useState<any[]>([]);

  const load = async () => {
    setLoading(true);
    try {
      const data = await api.listTasks(scope);
      setTasks(data.tasks || []);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, [scope.agentId, scope.bindingId]);

  return (
    <ConsolePage
        title="任务调度"
        actions={<PageToolbar><Button onClick={() => void load()}>刷新</Button></PageToolbar>}
      >
      <DataTableShell
        title="任务列表"
        rowKey={(row) => row.id || row.task_id || row.name || JSON.stringify(row)}
        loading={loading}
        dataSource={tasks}
        pagination={{ pageSize: 20 }}
        columns={[
          { title: '任务标识', render: (_, row) => row.id || row.task_id || '-' },
          { title: '名称', render: (_, row) => row.name || '-' },
          { title: '状态', render: (_, row) => <StatusTag status={row.status}>{row.status || '未知'}</StatusTag> },
          { title: '下次执行', render: (_, row) => row.next_run_at || row.next_run || '-' },
        ]}
        expandable={{ expandedRowRender: (row) => <AdvancedJsonPanel title="完整任务 JSON" value={row} defaultOpen /> }}
      />
    </ConsolePage>
  );
}
