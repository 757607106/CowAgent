import { Button, Card, DatePicker, Segmented, Select, Statistic, Tag, message } from 'antd';
import { useEffect, useMemo, useState } from 'react';
import { EChartCard } from '../components/EChartCard';
import { AdvancedJsonPanel, ConsolePage, DataTableShell, PageToolbar } from '../components/console';
import { displayAgentName, useRuntimeScope } from '../context/runtime';
import { api } from '../services/api';
import type {
  AgentItem,
  UsageAnalytics,
  UsageBucket,
  UsageCountItem,
  UsageDimensionSummary,
  UsageRecordItem,
  UsageSummary,
} from '../types';

const { RangePicker } = DatePicker;

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

const EMPTY_ANALYTICS: UsageAnalytics = {
  bucket: 'day',
  start: '',
  end: '',
  summary: EMPTY_SUMMARY,
  time_series: [],
  agents: [],
  models: [],
  tools: [],
  mcp_tools: [],
  skills: [],
};

const BUCKET_OPTIONS: Array<{ label: string; value: UsageBucket }> = [
  { label: '小时', value: 'hour' },
  { label: '天', value: 'day' },
  { label: '周', value: 'week' },
  { label: '月', value: 'month' },
  { label: '年', value: 'year' },
];

const CHART_COLORS = {
  primary: '#1a6ff5',
  success: '#10b981',
  warning: '#f59e0b',
  error: '#ef4444',
  text: '#4b5362',
  muted: '#8891a0',
  border: '#e4e8ee',
};

function formatNumber(value: number) {
  return Number(value || 0).toLocaleString('zh-CN');
}

function compactNumber(value: number) {
  if (value >= 100000000) return `${(value / 100000000).toFixed(1)}亿`;
  if (value >= 10000) return `${(value / 10000).toFixed(1)}万`;
  return String(value || 0);
}

function formatCost(value: number) {
  return Number(value || 0).toFixed(6);
}

function normalizeDateRange(dateStrings: [string, string]) {
  const [start, end] = dateStrings;
  return [start || '', end || ''] as [string, string];
}

function metricTooltipLabel(value: unknown) {
  return typeof value === 'number' ? formatNumber(value) : String(value ?? '');
}

function buildTrendOption(points: UsageDimensionSummary[]) {
  const labels = points.map((item) => item.key);
  return {
    color: [CHART_COLORS.primary, CHART_COLORS.success, CHART_COLORS.warning],
    tooltip: {
      trigger: 'axis',
      valueFormatter: metricTooltipLabel,
    },
    legend: {
      top: 0,
      right: 0,
      itemWidth: 10,
      itemHeight: 10,
      textStyle: { color: CHART_COLORS.text },
    },
    grid: { top: 40, right: 18, bottom: 24, left: 48, containLabel: true },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: labels,
      axisLine: { lineStyle: { color: CHART_COLORS.border } },
      axisTick: { show: false },
      axisLabel: { color: CHART_COLORS.muted },
    },
    yAxis: {
      type: 'value',
      axisLabel: { color: CHART_COLORS.muted, formatter: compactNumber },
      splitLine: { lineStyle: { color: CHART_COLORS.border } },
    },
    series: [
      {
        name: '总 Token',
        type: 'line',
        smooth: true,
        symbol: 'circle',
        symbolSize: 5,
        data: points.map((item) => item.total_tokens),
        areaStyle: { opacity: 0.08 },
      },
      {
        name: '输入',
        type: 'line',
        smooth: true,
        symbol: 'circle',
        symbolSize: 4,
        data: points.map((item) => item.prompt_tokens),
      },
      {
        name: '输出',
        type: 'line',
        smooth: true,
        symbol: 'circle',
        symbolSize: 4,
        data: points.map((item) => item.completion_tokens),
      },
    ],
  };
}

function buildTokenBarOption(items: UsageDimensionSummary[], labelMap?: Map<string, string>) {
  const data = items.slice(0, 10);
  const labels = data.map((item) => labelMap?.get(item.key) || item.key);
  return {
    color: [CHART_COLORS.primary, CHART_COLORS.success],
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      valueFormatter: metricTooltipLabel,
    },
    grid: { top: 16, right: 18, bottom: 28, left: 48, containLabel: true },
    xAxis: {
      type: 'category',
      data: labels,
      axisLine: { lineStyle: { color: CHART_COLORS.border } },
      axisTick: { show: false },
      axisLabel: { color: CHART_COLORS.muted, interval: 0, overflow: 'truncate', width: 80 },
    },
    yAxis: {
      type: 'value',
      axisLabel: { color: CHART_COLORS.muted, formatter: compactNumber },
      splitLine: { lineStyle: { color: CHART_COLORS.border } },
    },
    series: [
      {
        name: '总 Token',
        type: 'bar',
        barMaxWidth: 28,
        data: data.map((item) => item.total_tokens),
      },
    ],
  };
}

function buildCountBarOption(items: UsageCountItem[]) {
  const data = items.slice(0, 10).reverse();
  return {
    color: [CHART_COLORS.primary],
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      valueFormatter: metricTooltipLabel,
    },
    grid: { top: 10, right: 18, bottom: 18, left: 96, containLabel: true },
    xAxis: {
      type: 'value',
      axisLabel: { color: CHART_COLORS.muted, formatter: compactNumber },
      splitLine: { lineStyle: { color: CHART_COLORS.border } },
    },
    yAxis: {
      type: 'category',
      data: data.map((item) => item.key),
      axisLine: { lineStyle: { color: CHART_COLORS.border } },
      axisTick: { show: false },
      axisLabel: { color: CHART_COLORS.muted, overflow: 'truncate', width: 110 },
    },
    series: [
      {
        name: '调用次数',
        type: 'bar',
        barMaxWidth: 18,
        data: data.map((item) => item.count),
      },
    ],
  };
}

export default function UsagePage() {
  const { tenantId } = useRuntimeScope();
  const [agents, setAgents] = useState<AgentItem[]>([]);
  const [agentId, setAgentId] = useState('');
  const [bucket, setBucket] = useState<UsageBucket>('day');
  const [dateRange, setDateRange] = useState<[string, string]>(['', '']);
  const [model, setModel] = useState('');
  const [tenantSummary, setTenantSummary] = useState<UsageSummary>(EMPTY_SUMMARY);
  const [scopeSummary, setScopeSummary] = useState<UsageSummary>(EMPTY_SUMMARY);
  const [analytics, setAnalytics] = useState<UsageAnalytics>(EMPTY_ANALYTICS);
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

  const modelOptions = useMemo(
    () => analytics.models.map((item) => ({
      label: item.key,
      value: item.key,
    })),
    [analytics.models],
  );

  const trendOption = useMemo(() => buildTrendOption(analytics.time_series), [analytics.time_series]);
  const agentOption = useMemo(() => buildTokenBarOption(analytics.agents, agentNameById), [analytics.agents, agentNameById]);
  const modelOption = useMemo(() => buildTokenBarOption(analytics.models), [analytics.models]);
  const toolOption = useMemo(() => buildCountBarOption(analytics.tools), [analytics.tools]);
  const mcpOption = useMemo(() => buildCountBarOption(analytics.mcp_tools), [analytics.mcp_tools]);
  const skillOption = useMemo(() => buildCountBarOption(analytics.skills), [analytics.skills]);

  const formatAgentName = (value?: string) => {
    const normalized = (value || '').trim();
    if (!normalized) return '';
    return agentNameById.get(normalized) || normalized;
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
    const [start, end] = dateRange;
    setLoading(true);
    try {
      const scopedAnalyticsRequest = api.getUsageAnalytics(tenantId, agentId, bucket, start, end, model, 10);
      const tenantAnalyticsRequest = agentId
        ? api.getUsageAnalytics(tenantId, '', bucket, start, end, model, 10)
        : scopedAnalyticsRequest;
      const [tenantAnalyticsData, scopedAnalyticsData, usageData] = await Promise.all([
        tenantAnalyticsRequest,
        scopedAnalyticsRequest,
        api.listUsage(tenantId, agentId, '', 100, start, end, model, bucket),
      ]);
      setTenantSummary(tenantAnalyticsData.analytics?.summary || EMPTY_SUMMARY);
      setScopeSummary(scopedAnalyticsData.analytics?.summary || EMPTY_SUMMARY);
      setAnalytics(scopedAnalyticsData.analytics || EMPTY_ANALYTICS);
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
  }, [tenantId, agentId, bucket, dateRange[0], dateRange[1], model]);

  return (
    <ConsolePage
      title="用量统计"
      actions={(
        <PageToolbar>
          <Segmented
            className="usage-bucket-filter"
            value={bucket}
            options={BUCKET_OPTIONS}
            onChange={(value) => setBucket(value as UsageBucket)}
          />
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
          <Select
            allowClear
            showSearch
            className="usage-model-filter"
            value={model || undefined}
            placeholder="全部模型"
            optionFilterProp="label"
            onChange={(value) => setModel(value || '')}
            options={modelOptions}
          />
          <RangePicker
            allowClear
            className="usage-range-filter"
            placeholder={['开始日期', '结束日期']}
            onChange={(_dates, dateStrings) => setDateRange(normalizeDateRange(dateStrings as [string, string]))}
            format="YYYY-MM-DD"
          />
          <Button onClick={() => void loadUsage()}>刷新</Button>
        </PageToolbar>
      )}
    >
      <div className="operations-summary-grid usage-summary-grid">
        <Card className="operations-summary-card">
          <Statistic title="租户总 Token" value={tenantSummary.total_tokens} formatter={(value) => formatNumber(Number(value))} loading={loading} />
        </Card>
        <Card className="operations-summary-card">
          <Statistic title="租户总费用" value={tenantSummary.estimated_cost} precision={6} loading={loading} />
        </Card>
        <Card className="operations-summary-card">
          <Statistic title={agentId ? 'AI 员工 Token' : '筛选 Token'} value={scopeSummary.total_tokens} formatter={(value) => formatNumber(Number(value))} loading={loading} />
        </Card>
        <Card className="operations-summary-card">
          <Statistic title="请求数" value={scopeSummary.request_count} formatter={(value) => formatNumber(Number(value))} loading={loading} />
        </Card>
        <Card className="operations-summary-card">
          <Statistic title="工具调用" value={scopeSummary.tool_call_count} formatter={(value) => formatNumber(Number(value))} loading={loading} />
        </Card>
        <Card className="operations-summary-card">
          <Statistic title="MCP 调用" value={scopeSummary.mcp_call_count} formatter={(value) => formatNumber(Number(value))} loading={loading} />
        </Card>
      </div>

      <section className="usage-chart-grid">
        <EChartCard
          title="Token 趋势"
          className="usage-chart-wide"
          option={trendOption}
          empty={!analytics.time_series.length}
          loading={loading}
          height="20rem"
        />
        <EChartCard
          title="AI 员工 Token 排行"
          option={agentOption}
          empty={!analytics.agents.length}
          loading={loading || !agentsLoaded}
        />
        <EChartCard
          title="模型 Token 排行"
          option={modelOption}
          empty={!analytics.models.length}
          loading={loading}
        />
        <EChartCard
          title="工具调用排行"
          option={toolOption}
          empty={!analytics.tools.length}
          loading={loading}
        />
        <EChartCard
          title="MCP 工具排行"
          option={mcpOption}
          empty={!analytics.mcp_tools.length}
          loading={loading}
        />
        <EChartCard
          title="Skill 使用排行"
          option={skillOption}
          empty={!analytics.skills.length}
          loading={loading}
        />
      </section>

      <DataTableShell<UsageRecordItem>
        className="usage-table-shell"
        title="用量明细"
        rowKey="event_id"
        loading={loading || !agentsLoaded}
        dataSource={records}
        pagination={{ pageSize: 20, showSizeChanger: false }}
        scroll={{ x: 1180, y: 'max(320px, calc(100vh - 560px))' }}
        columns={[
          { title: '时间', dataIndex: 'created_at', width: 170 },
          { title: 'AI 员工', dataIndex: 'agent_id', width: 140, render: renderAgentName },
          { title: '模型', dataIndex: 'model', width: 150, render: (value: string) => (value ? <Tag color="blue">{value}</Tag> : '-') },
          { title: '总 Token', dataIndex: 'total_tokens', width: 110, render: (value: number) => formatNumber(value) },
          { title: '输入', dataIndex: 'prompt_tokens', width: 100, render: (value: number) => formatNumber(value) },
          { title: '输出', dataIndex: 'completion_tokens', width: 100, render: (value: number) => formatNumber(value) },
          { title: '工具', dataIndex: 'tool_call_count', width: 90 },
          { title: 'MCP', dataIndex: 'mcp_call_count', width: 90 },
          { title: '错误', dataIndex: 'tool_error_count', width: 90 },
          { title: '费用', dataIndex: 'estimated_cost', width: 110, render: (value: number) => formatCost(value) },
        ]}
        expandable={{
          expandedRowRender: (row) => <AdvancedJsonPanel title="诊断信息" value={row} defaultOpen />,
        }}
      />
    </ConsolePage>
  );
}
