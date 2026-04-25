import { Button, Card, Col, DatePicker, Row, Select, Space, Statistic, Table, Tag, message } from 'antd';
import { useEffect, useState } from 'react';
import { PageTitle } from '../components/PageTitle';
import { useRuntimeScope } from '../context/runtime';
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
  const [loading, setLoading] = useState(false);

  const loadAgents = async () => {
    const data = await api.listAgents(tenantId);
    setAgents(data.agents || []);
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
    <Card>
      <PageTitle
        title="用量统计"
        description="查看当前租户与不同 Agent 的 Token、工具、MCP 和费用消耗。"
        extra={(
          <Space wrap>
            <Select
              allowClear
              style={{ width: 240 }}
              value={agentId || undefined}
              placeholder="全部 Agent"
              onChange={(value) => setAgentId(value || '')}
              options={agents.map((agent) => ({
                label: `${agent.name} (${agent.agent_id})`,
                value: agent.agent_id,
              }))}
            />
            <DatePicker
              allowClear
              style={{ width: 160 }}
              placeholder="选择日期"
              onChange={(_date, dateString) => setDay(typeof dateString === 'string' ? dateString : '')}
              format="YYYY-MM-DD"
            />
            <Button onClick={() => void loadUsage()}>刷新</Button>
          </Space>
        )}
      />

      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col xs={12} lg={6}>
          <Statistic title="租户总 Token" value={tenantSummary.total_tokens} loading={loading} />
        </Col>
        <Col xs={12} lg={6}>
          <Statistic title="租户总费用" value={tenantSummary.estimated_cost} precision={6} loading={loading} />
        </Col>
        <Col xs={12} lg={6}>
          <Statistic title={agentId ? 'Agent Token' : '筛选 Token'} value={scopeSummary.total_tokens} loading={loading} />
        </Col>
        <Col xs={12} lg={6}>
          <Statistic title="MCP 调用" value={scopeSummary.mcp_call_count} loading={loading} />
        </Col>
      </Row>

      <Table<UsageRecordItem>
        rowKey="event_id"
        loading={loading}
        dataSource={records}
        pagination={{ pageSize: 20 }}
        scroll={{ x: 1100 }}
        columns={[
          { title: '时间', dataIndex: 'created_at', width: 170 },
          { title: 'Agent', dataIndex: 'agent_id', width: 140 },
          { title: '模型', dataIndex: 'model', width: 150, render: (value: string) => (value ? <Tag color="blue">{value}</Tag> : '-') },
          { title: '总 Token', dataIndex: 'total_tokens', width: 110 },
          { title: '输入', dataIndex: 'prompt_tokens', width: 100 },
          { title: '输出', dataIndex: 'completion_tokens', width: 100 },
          { title: '工具', dataIndex: 'tool_call_count', width: 90 },
          { title: 'MCP', dataIndex: 'mcp_call_count', width: 90 },
          { title: '错误', dataIndex: 'tool_error_count', width: 90 },
          { title: '费用', dataIndex: 'estimated_cost', width: 110, render: (value: number) => Number(value || 0).toFixed(6) },
          { title: '请求', dataIndex: 'request_id', width: 190, ellipsis: true },
        ]}
      />
    </Card>
  );
}
