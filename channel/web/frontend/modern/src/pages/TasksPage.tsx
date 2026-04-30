import {
  Button,
  DatePicker,
  Drawer,
  Form,
  Input,
  InputNumber,
  Popconfirm,
  Segmented,
  Select,
  Space,
  Switch,
  Tag,
  Typography,
  message,
} from 'antd';
import {
  DeleteOutlined,
  EditOutlined,
  HistoryOutlined,
  PauseCircleOutlined,
  PlayCircleOutlined,
  PlusOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import dayjs, { type Dayjs } from 'dayjs';
import { useEffect, useMemo, useState } from 'react';
import { useRuntimeScope } from '../context/runtime';
import { AdvancedJsonPanel, ConsolePage, DataTableShell, PageToolbar, StatusTag } from '../components/console';
import { api } from '../services/api';
import type { ChannelConfigItem, ScheduledTaskItem, ScheduledTaskRunItem } from '../types';

type TaskActionType = 'send_message' | 'agent_task';
type TaskScheduleType = 'once' | 'interval' | 'cron';
type IntervalUnit = 'seconds' | 'minutes' | 'hours' | 'days';

interface TaskFormValues {
  name: string;
  enabled: boolean;
  action_type: TaskActionType;
  content?: string;
  task_description?: string;
  receiver: string;
  receiver_name?: string;
  channel_type: string;
  channel_config_id?: string;
  is_group: boolean;
  schedule_type: TaskScheduleType;
  run_at?: Dayjs;
  interval_amount?: number;
  interval_unit?: IntervalUnit;
  cron_expression?: string;
}

const ACTION_OPTIONS = [
  { label: '固定消息', value: 'send_message' },
  { label: 'AI 任务', value: 'agent_task' },
];

const SCHEDULE_OPTIONS = [
  { label: '一次性', value: 'once' },
  { label: '固定间隔', value: 'interval' },
  { label: 'Cron', value: 'cron' },
];

const STATUS_OPTIONS = [
  { label: '全部状态', value: '' },
  { label: '待执行', value: 'scheduled' },
  { label: '已暂停', value: 'disabled' },
  { label: '失败', value: 'failed' },
  { label: '已完成', value: 'completed' },
];

const CHANNEL_FALLBACKS = [
  { label: 'Web', value: 'web' },
  { label: '微信', value: 'wechatmp' },
  { label: '企业微信', value: 'wecom_bot' },
  { label: '飞书', value: 'feishu' },
  { label: '钉钉', value: 'dingtalk' },
  { label: 'QQ', value: 'qq' },
];

const INTERVAL_UNITS = [
  { label: '秒', value: 'seconds' },
  { label: '分钟', value: 'minutes' },
  { label: '小时', value: 'hours' },
  { label: '天', value: 'days' },
];

function statusLabel(status?: string) {
  if (status === 'scheduled') return '待执行';
  if (status === 'disabled') return '已暂停';
  if (status === 'failed') return '失败';
  if (status === 'completed') return '已完成';
  if (status === 'idle') return '空闲';
  if (status === 'success') return '成功';
  if (status === 'running') return '执行中';
  return status || '未知';
}

function actionLabel(type?: string) {
  if (type === 'agent_task') return 'AI 任务';
  if (type === 'send_message') return '固定消息';
  return type || '未知';
}

function scheduleLabel(task: ScheduledTaskItem) {
  const schedule = task.schedule || { type: '' };
  if (schedule.type === 'once') return `一次性 ${toDateTimeText(schedule.run_at)}`;
  if (schedule.type === 'interval') return `每 ${formatInterval(Number(schedule.seconds || 0))}`;
  if (schedule.type === 'cron') return `Cron ${schedule.expression || '-'}`;
  return '未知';
}

function formatInterval(seconds: number) {
  if (seconds >= 86400 && seconds % 86400 === 0) return `${seconds / 86400} 天`;
  if (seconds >= 3600 && seconds % 3600 === 0) return `${seconds / 3600} 小时`;
  if (seconds >= 60 && seconds % 60 === 0) return `${seconds / 60} 分钟`;
  return `${seconds || 0} 秒`;
}

function toDateTimeText(value?: string) {
  if (!value) return '-';
  const parsed = dayjs(value);
  return parsed.isValid() ? parsed.format('YYYY-MM-DD HH:mm:ss') : value;
}

function secondsToInterval(seconds?: number): Pick<TaskFormValues, 'interval_amount' | 'interval_unit'> {
  const value = Number(seconds || 0);
  if (value >= 86400 && value % 86400 === 0) return { interval_amount: value / 86400, interval_unit: 'days' };
  if (value >= 3600 && value % 3600 === 0) return { interval_amount: value / 3600, interval_unit: 'hours' };
  if (value >= 60 && value % 60 === 0) return { interval_amount: value / 60, interval_unit: 'minutes' };
  return { interval_amount: value || 60, interval_unit: 'seconds' };
}

function intervalToSeconds(amount = 0, unit: IntervalUnit = 'seconds') {
  if (unit === 'days') return amount * 86400;
  if (unit === 'hours') return amount * 3600;
  if (unit === 'minutes') return amount * 60;
  return amount;
}

function buildInitialValues(task?: ScheduledTaskItem | null): TaskFormValues {
  const action = task?.action || { type: 'send_message' };
  const schedule = task?.schedule || { type: 'once' };
  const interval = secondsToInterval(schedule.seconds);
  return {
    name: task?.name || '',
    enabled: task?.enabled ?? true,
    action_type: (action.type === 'agent_task' ? 'agent_task' : 'send_message'),
    content: action.content || '',
    task_description: action.task_description || '',
    receiver: action.receiver || '',
    receiver_name: action.receiver_name || '',
    channel_type: action.channel_type || 'web',
    channel_config_id: action.channel_config_id || task?.channel_config_id || '',
    is_group: Boolean(action.is_group),
    schedule_type: (schedule.type === 'interval' || schedule.type === 'cron' ? schedule.type : 'once'),
    run_at: schedule.run_at ? dayjs(schedule.run_at) : dayjs().add(10, 'minute'),
    interval_amount: interval.interval_amount,
    interval_unit: interval.interval_unit,
    cron_expression: schedule.expression || '0 9 * * *',
  };
}

function buildPayload(values: TaskFormValues) {
  const payload: Record<string, unknown> = {
    name: values.name,
    enabled: values.enabled ?? true,
    action_type: values.action_type,
    receiver: values.receiver,
    receiver_name: values.receiver_name || values.receiver,
    channel_type: values.channel_type || 'web',
    channel_config_id: values.channel_config_id || '',
    is_group: values.is_group ?? false,
    schedule_type: values.schedule_type,
  };
  if (values.action_type === 'agent_task') {
    payload.task_description = values.task_description || '';
  } else {
    payload.content = values.content || '';
  }
  if (values.schedule_type === 'once') {
    payload.schedule_value = values.run_at?.format('YYYY-MM-DDTHH:mm:ss') || '';
  } else if (values.schedule_type === 'interval') {
    payload.schedule_value = String(intervalToSeconds(values.interval_amount, values.interval_unit));
  } else {
    payload.schedule_value = values.cron_expression || '';
  }
  return payload;
}

export default function TasksPage() {
  const { scope, tenantId, authUser } = useRuntimeScope();
  const canManage = authUser?.role === 'owner' || authUser?.role === 'admin';
  const [loading, setLoading] = useState(false);
  const [tasks, setTasks] = useState<ScheduledTaskItem[]>([]);
  const [channelConfigs, setChannelConfigs] = useState<ChannelConfigItem[]>([]);
  const [statusFilter, setStatusFilter] = useState('');
  const [scheduleFilter, setScheduleFilter] = useState('');
  const [actionFilter, setActionFilter] = useState('');
  const [keyword, setKeyword] = useState('');
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [editing, setEditing] = useState<ScheduledTaskItem | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [runsOpen, setRunsOpen] = useState(false);
  const [runsLoading, setRunsLoading] = useState(false);
  const [runsTask, setRunsTask] = useState<ScheduledTaskItem | null>(null);
  const [runs, setRuns] = useState<ScheduledTaskRunItem[]>([]);
  const [form] = Form.useForm<TaskFormValues>();
  const actionType = Form.useWatch('action_type', form);
  const scheduleType = Form.useWatch('schedule_type', form);

  const load = async () => {
    setLoading(true);
    try {
      const [taskData, channelData] = await Promise.all([
        api.listTasks(scope),
        api.listChannelConfigs(tenantId).catch(() => ({ channel_configs: [] as ChannelConfigItem[] })),
      ]);
      setTasks(taskData.tasks || []);
      setChannelConfigs(channelData.channel_configs || []);
    } finally {
      setLoading(false);
    }
  };

  const channelOptions = useMemo(() => {
    const configured = channelConfigs.map((item) => ({
      label: item.name || item.label || item.channel_type,
      value: item.channel_type,
      channel_config_id: item.channel_config_id,
    }));
    const seen = new Set(configured.map((item) => item.value));
    return [
      ...configured,
      ...CHANNEL_FALLBACKS.filter((item) => !seen.has(item.value)),
    ];
  }, [channelConfigs]);

  const filteredTasks = useMemo(() => {
    const normalizedKeyword = keyword.trim().toLowerCase();
    return tasks.filter((task) => {
      if (statusFilter && task.status !== statusFilter) return false;
      if (scheduleFilter && task.schedule?.type !== scheduleFilter) return false;
      if (actionFilter && task.action?.type !== actionFilter) return false;
      if (!normalizedKeyword) return true;
      return [task.id, task.name, task.action?.receiver, task.action?.receiver_name]
        .some((value) => String(value || '').toLowerCase().includes(normalizedKeyword));
    });
  }, [actionFilter, keyword, scheduleFilter, statusFilter, tasks]);

  const openCreate = () => {
    setEditing(null);
    form.setFieldsValue(buildInitialValues(null));
    setDrawerOpen(true);
  };

  const openEdit = (task: ScheduledTaskItem) => {
    setEditing(task);
    form.setFieldsValue(buildInitialValues(task));
    setDrawerOpen(true);
  };

  const submit = async () => {
    const values = await form.validateFields();
    setSubmitting(true);
    try {
      if (editing) {
        await api.updateTask(scope, editing.id, buildPayload(values));
        message.success('任务已更新');
      } else {
        await api.createTask(scope, buildPayload(values));
        message.success('任务已创建');
      }
      setDrawerOpen(false);
      await load();
    } finally {
      setSubmitting(false);
    }
  };

  const toggleTask = async (task: ScheduledTaskItem) => {
    if (task.enabled) {
      await api.disableTask(scope, task.id);
      message.success('任务已暂停');
    } else {
      await api.enableTask(scope, task.id);
      message.success('任务已启用');
    }
    await load();
  };

  const deleteTask = async (task: ScheduledTaskItem) => {
    await api.deleteTask(scope, task.id);
    message.success('任务已删除');
    await load();
  };

  const runTaskOnce = async (task: ScheduledTaskItem) => {
    await api.runTaskOnce(scope, task.id);
    message.success('任务已触发');
    await load();
  };

  const openRuns = async (task: ScheduledTaskItem) => {
    setRunsTask(task);
    setRunsOpen(true);
    setRunsLoading(true);
    try {
      const data = await api.listTaskRuns(scope, task.id);
      setRuns(data.runs || []);
    } finally {
      setRunsLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, [scope.agentId, scope.bindingId, scope.tenantId]);

  return (
    <ConsolePage
      title="任务调度"
      className="tasks-page"
      actions={(
        <PageToolbar>
          <Button icon={<ReloadOutlined />} onClick={() => void load()}>刷新</Button>
          {canManage ? <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>新建任务</Button> : null}
        </PageToolbar>
      )}
    >
      <div className="tasks-filter-bar">
        <Segmented
          value={statusFilter}
          onChange={(value) => setStatusFilter(String(value))}
          options={STATUS_OPTIONS}
        />
        <Select
          value={scheduleFilter}
          onChange={setScheduleFilter}
          options={[{ label: '全部类型', value: '' }, ...SCHEDULE_OPTIONS]}
          className="tasks-filter-select"
          aria-label="调度类型"
        />
        <Select
          value={actionFilter}
          onChange={setActionFilter}
          options={[{ label: '全部动作', value: '' }, ...ACTION_OPTIONS]}
          className="tasks-filter-select"
          aria-label="执行动作"
        />
        <Input.Search
          allowClear
          value={keyword}
          onChange={(event) => setKeyword(event.target.value)}
          className="tasks-filter-search"
          placeholder="搜索任务、接收人"
        />
      </div>

      <DataTableShell<ScheduledTaskItem>
        title={`任务列表 (${filteredTasks.length})`}
        rowKey="id"
        loading={loading}
        dataSource={filteredTasks}
        pagination={{ pageSize: 12 }}
        scroll={{ x: 'max-content' }}
        columns={[
          {
            title: '任务',
            dataIndex: 'name',
            width: 220,
            render: (value: string, row) => (
              <span className="entity-title-cell">
                <span className="entity-title-cell-main">{value || row.id}</span>
                <span className="entity-title-cell-meta">{row.id}</span>
              </span>
            ),
          },
          { title: '状态', dataIndex: 'status', width: 100, render: (value: string) => <StatusTag status={value}>{statusLabel(value)}</StatusTag> },
          { title: '调度', width: 180, render: (_, row) => scheduleLabel(row) },
          { title: '动作', width: 100, render: (_, row) => <Tag color={row.action?.type === 'agent_task' ? 'purple' : 'blue'}>{actionLabel(row.action?.type)}</Tag> },
          { title: '渠道', width: 110, render: (_, row) => row.action?.channel_type || '-' },
          { title: '接收人', width: 180, render: (_, row) => row.action?.receiver_name || row.action?.receiver || '-' },
          { title: '下次执行', width: 170, render: (_, row) => toDateTimeText(row.next_run_at) },
          { title: '上次执行', width: 170, render: (_, row) => toDateTimeText(row.last_run_at) },
          {
            title: '操作',
            fixed: 'right',
            width: 280,
            render: (_, row) => (
              <Space size={6} className="task-action-cell">
                <Button size="small" icon={<HistoryOutlined />} onClick={() => void openRuns(row)} />
                {canManage ? (
                  <>
                    <Button size="small" icon={<PlayCircleOutlined />} onClick={() => void runTaskOnce(row)} />
                    <Button size="small" icon={row.enabled ? <PauseCircleOutlined /> : <PlayCircleOutlined />} onClick={() => void toggleTask(row)}>
                      {row.enabled ? '暂停' : '启用'}
                    </Button>
                    <Button size="small" icon={<EditOutlined />} onClick={() => openEdit(row)}>编辑</Button>
                    <Popconfirm title="确认删除该任务？" onConfirm={() => void deleteTask(row)}>
                      <Button size="small" danger icon={<DeleteOutlined />} />
                    </Popconfirm>
                  </>
                ) : null}
              </Space>
            ),
          },
        ]}
        expandable={{
          expandedRowRender: (row) => <AdvancedJsonPanel title="完整任务 JSON" value={row} defaultOpen />,
        }}
      />

      <Drawer
        open={drawerOpen}
        title={editing ? '编辑任务' : '新建任务'}
        width={560}
        onClose={() => setDrawerOpen(false)}
        destroyOnClose
        extra={(
          <Space>
            <Button onClick={() => setDrawerOpen(false)}>取消</Button>
            <Button type="primary" loading={submitting} onClick={() => void submit()}>保存</Button>
          </Space>
        )}
      >
        <Form form={form} layout="vertical">
          <Form.Item name="name" label="任务名称" rules={[{ required: true, message: '请输入任务名称' }]}>
            <Input aria-label="任务名称" />
          </Form.Item>
          <Form.Item name="enabled" label="启用" valuePropName="checked">
            <Switch aria-label="启用任务" />
          </Form.Item>
          <Form.Item name="action_type" label="执行内容" rules={[{ required: true }]}>
            <Segmented options={ACTION_OPTIONS} block />
          </Form.Item>
          {actionType === 'agent_task' ? (
            <Form.Item name="task_description" label="AI 任务" rules={[{ required: true, message: '请输入 AI 任务' }]}>
              <Input.TextArea rows={4} aria-label="AI 任务" />
            </Form.Item>
          ) : (
            <Form.Item name="content" label="固定消息" rules={[{ required: true, message: '请输入固定消息' }]}>
              <Input.TextArea rows={4} aria-label="固定消息" />
            </Form.Item>
          )}
          <Space size={12} className="tasks-form-row">
            <Form.Item name="channel_type" label="渠道" rules={[{ required: true }]}>
              <Select
                options={channelOptions}
                aria-label="渠道"
                onChange={(value) => {
                  const config = channelConfigs.find((item) => item.channel_type === value);
                  form.setFieldValue('channel_config_id', config?.channel_config_id || '');
                }}
              />
            </Form.Item>
            <Form.Item name="channel_config_id" label="渠道配置">
              <Select
                allowClear
                options={channelConfigs.map((item) => ({ label: item.name || item.channel_config_id, value: item.channel_config_id }))}
                aria-label="渠道配置"
              />
            </Form.Item>
          </Space>
          <Space size={12} className="tasks-form-row">
            <Form.Item name="receiver" label="接收人 / 会话 ID" rules={[{ required: true, message: '请输入接收人或会话 ID' }]}>
              <Input aria-label="接收人 / 会话 ID" />
            </Form.Item>
            <Form.Item name="receiver_name" label="显示名称">
              <Input aria-label="显示名称" />
            </Form.Item>
          </Space>
          <Form.Item name="is_group" label="群聊" valuePropName="checked">
            <Switch aria-label="群聊" />
          </Form.Item>
          <Form.Item name="schedule_type" label="调度方式" rules={[{ required: true }]}>
            <Segmented options={SCHEDULE_OPTIONS} block />
          </Form.Item>
          {scheduleType === 'once' ? (
            <Form.Item name="run_at" label="执行时间" rules={[{ required: true, message: '请选择执行时间' }]}>
              <DatePicker showTime format="YYYY-MM-DD HH:mm:ss" className="tasks-full-width-control" aria-label="执行时间" />
            </Form.Item>
          ) : null}
          {scheduleType === 'interval' ? (
            <Space size={12} className="tasks-form-row">
              <Form.Item name="interval_amount" label="间隔" rules={[{ required: true, message: '请输入间隔' }]}>
                <InputNumber min={1} precision={0} className="tasks-full-width-control" aria-label="间隔" />
              </Form.Item>
              <Form.Item name="interval_unit" label="单位" rules={[{ required: true }]}>
                <Select options={INTERVAL_UNITS} aria-label="单位" />
              </Form.Item>
            </Space>
          ) : null}
          {scheduleType === 'cron' ? (
            <Form.Item name="cron_expression" label="Cron 表达式" rules={[{ required: true, message: '请输入 Cron 表达式' }]}><Input aria-label="Cron 表达式" /></Form.Item>
          ) : null}
        </Form>
      </Drawer>

      <Drawer
        open={runsOpen}
        title={runsTask ? `执行记录：${runsTask.name}` : '执行记录'}
        width={720}
        onClose={() => setRunsOpen(false)}
      >
        <DataTableShell<ScheduledTaskRunItem>
          compact
          rowKey="run_id"
          loading={runsLoading}
          dataSource={runs}
          pagination={{ pageSize: 10 }}
          columns={[
            { title: '状态', dataIndex: 'status', width: 90, render: (value: string) => <StatusTag status={value}>{statusLabel(value)}</StatusTag> },
            { title: '触发', dataIndex: 'trigger_type', width: 90, render: (value: string) => (value === 'manual' ? '手动' : '计划') },
            { title: '开始时间', dataIndex: 'started_at', width: 170, render: (value: string) => toDateTimeText(value) },
            { title: '耗时', dataIndex: 'duration_ms', width: 90, render: (value: number) => `${value || 0} ms` },
            {
              title: '结果',
              render: (_, row) => (
                row.error_message ? <Typography.Text type="danger">{row.error_message}</Typography.Text> : <Typography.Text>完成</Typography.Text>
              ),
            },
          ]}
          expandable={{
            expandedRowRender: (row) => <AdvancedJsonPanel title="执行详情" value={row} defaultOpen />,
          }}
        />
      </Drawer>
    </ConsolePage>
  );
}
