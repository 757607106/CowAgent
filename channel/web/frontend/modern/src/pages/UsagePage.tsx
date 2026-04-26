import { Button, Card, DatePicker, Select, Statistic, Tag, message } from 'antd';
import { useEffect, useMemo, useState } from 'react';
import { AdvancedJsonPanel, ConsolePage, DataTableShell, PageToolbar } from '../components/console';
import { displayAgentName, useRuntimeScope } from '../context/runtime';
import { api } from '../services/api';
import type { AgentItem, UsageRecordItem, UsageSummary } from '../types';

const EMPTY_SUMMARY: UsageSummary = {
  request_count: 0,
  prompt_tokens: 0,
  completion_tokens: 0,
  total_tokens: 0,
  provider_request_count: 0,
  estimated_request_count: 0,
  tool_call_count: 0,
  mcp_call_count: 0,
  tool_error_count: 0,
  tool_execution_time_ms: 0,
  estimated_cost: 0,
};

export default function UsagePage() {
  const { tenantId } = useRuntimeScope();
  const [agents, setAgents] = useState<AgentItem[]>([]);
  const [agentId, setAgentId] = useState('');
  const [day, setDay] = useState('');
  const [tenantSummary, setTenantSummary] = useState<UsageSummary>(EMPTY_SUMMARY);
  const [scopeSummary, setScopeSummary] = useState<UsageSummary>(EMPTY_SUMMARY);
  const [records, setRecords] = useState<UsageRecordItem[]>([]);
  const [agentsLoaded, setAgentsLoaded] = useState(false);
  const [loading, setLoading] = useState(false);

  const agentNameById = useMemo(
    () => new Map(agents.map((agent) => [agent.agent_id, displayAgentName(agent.agent_id, agent.name)])),
    [agents],
  );

  const agentOptions = useMemo(
    () => agents.map((agent) => ({
      label: displayAgentName(agent.agent_id, agent.name),
      value: agent.agent_id,
    })),
    [agents],
  );

  const formatAgentName = (value?: string) => {
    const normalized = (value || '').trim();
    if (!normalized) return '';
    return agentNameById.get(normalized) || '';
  };

  const renderAgentName = (value: string) => (
    <span className="usage-agent-name">
      {formatAgentName(value)}
    </span>
  );

  const loadAgents = async () => {
    setAgentsLoaded(false);
    try {
      const data = await api.listAgents(tenantId);
      setAgents(data.agents || []);
    } catch (error) {
      message.error(error instanceof Error ? error.message : '加载 AI 员工失败');
    } finally {
      setAgentsLoaded(true);
    }
  };

  const loadUsage = async () => {
    setLoading(true);
    try {
      const [tenantCost, scopedCost, usageData] = await Promise.all([
        api.getCostSummary(tenantId, '', day),
        api.getCostSummary(tenantId, agentId, day),
        api.listUsage(tenantId, agentId, day, 100),
      ]);
      setTenantSummary(tenantCost.summary || EMPTY_SUMMARY);
      setScopeSummary(scopedCost.summary || EMPTY_SUMMARY);
      setRecords(usageData.usage || []);
    } catch (error) {
      message.error(error instanceof Error ? error.message : '加载用量失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadAgents();
  }, [tenantId]);

  useEffect(() => {
    void loadUsage();
  }, [tenantId, agentId, day]);

  return (
    <ConsolePage
        title="用量统计"
        actions={(
          <PageToolbar>
            <Select
              allowClear
              showSearch
              className="usage-agent-filter"
              value={agentId || undefined}
              placeholder="全部 AI 员工"
              optionFilterProp="label"
              labelRender={(item) => formatAgentName(String(item.value || ''))}
              onChange={(value) => setAgentId(value || '')}
              options={agentOptions}
            />
            <DatePicker
              allowClear
              className="usage-day-filter"
              placeholder="选择日期"
              onChange={(_date, dateString) => setDay(typeof dateString === 'string' ? dateString : '')}
              format="YYYY-MM-DD"
            />
            <Button onClick={() => void loadUsage()}>刷新</Button>
          </PageToolbar>
        )}
      >

      <div className="operations-summary-grid">
        <Card className="operations-summary-card">
          <Statistic title="租户总 Token" value={tenantSummary.total_tokens} loading={loading} />
        </Card>
        <Card className="operations-summary-card">
          <Statistic title="租户总费用" value={tenantSummary.estimated_cost} precision={6} loading={loading} />
        </Card>
        <Card className="operations-summary-card">
          <Statistic title={agentId ? 'AI 员工 Token' : '筛选 Token'} value={scopeSummary.total_tokens} loading={loading} />
        </Card>
        <Card className="operations-summary-card">
          <Statistic title="MCP 调用" value={scopeSummary.mcp_call_count} loading={loading} />
        </Card>
      </div>

      <DataTableShell<UsageRecordItem>
        className="usage-table-shell"
        title="用量明细"
        rowKey="event_id"
        loading={loading || !agentsLoaded}
        dataSource={records}
        pagination={{ pageSize: 20, showSizeChanger: false }}
        scroll={{ x: 1100, y: 'max(360px, calc(100vh - 430px))' }}
        columns={[
          { title: '时间', dataIndex: 'created_at', width: 170 },
          { title: 'AI 员工', dataIndex: 'agent_id', width: 140, render: renderAgentName },
          { title: '模型', dataIndex: 'model', width: 150, render: (value: string) => (value ? <Tag color="blue">{value}</Tag> : '-') },
          { title: '总 Token', dataIndex: 'total_tokens', width: 110 },
          { title: '输入', dataIndex: 'prompt_tokens', width: 100 },
          { title: '输出', dataIndex: 'completion_tokens', width: 100 },
          { title: '工具', dataIndex: 'tool_call_count', width: 90 },
          { title: 'MCP', dataIndex: 'mcp_call_count', width: 90 },
          { title: '错误', dataIndex: 'tool_error_count', width: 90 },
          { title: '费用', dataIndex: 'estimated_cost', width: 110, render: (value: number) => Number(value || 0).toFixed(6) },
        ]}
        expandable={{
          expandedRowRender: (row) => <AdvancedJsonPanel title="诊断信息" value={row} defaultOpen />,
        }}
      />
    </ConsolePage>
  );
}
