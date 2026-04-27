import {
  CodeOutlined,
  DeleteOutlined,
  ReloadOutlined,
  SearchOutlined,
  SafetyCertificateOutlined,
} from '@ant-design/icons';
import {
  Badge,
  Button,
  Card,
  Empty,
  Input,
  Popconfirm,
  Select,
  Space,
  Statistic,
  Switch,
  Tag,
  Tooltip,
  Typography,
  message,
} from 'antd';
import { useEffect, useMemo, useState } from 'react';
import { useRuntimeScope } from '../context/runtime';
import { PageTitle } from '../components/PageTitle';
import { api } from '../services/api';
import type { SkillItem } from '../types';

type SkillStatusFilter = 'all' | 'enabled' | 'disabled';
type SkillSourceFilter = 'all' | 'builtin' | 'custom';

function enabledOf(skill: SkillItem): boolean {
  return Boolean(skill.enabled ?? skill.open ?? skill.active ?? skill.is_open);
}

function isBuiltinSkill(skill: SkillItem): boolean {
  return skill.source === 'builtin';
}

function displaySkillName(skill: SkillItem): string {
  return skill.display_name || skill.name;
}

function skillCategory(skill: SkillItem): string {
  return String(skill.category || (isBuiltinSkill(skill) ? '系统能力' : '本地技能'));
}

function sourceLabel(skill: SkillItem): string {
  if (isBuiltinSkill(skill)) return '系统内置';
  return skill.source ? String(skill.source) : '本地安装';
}

function sourceTag(skill: SkillItem) {
  if (isBuiltinSkill(skill)) return <Tag color="blue">系统内置</Tag>;
  return <Tag color="green">本地技能</Tag>;
}

export default function SkillsPage() {
  const { scope } = useRuntimeScope();
  const [loading, setLoading] = useState(false);
  const [savingName, setSavingName] = useState('');
  const [deletingName, setDeletingName] = useState('');
  const [skills, setSkills] = useState<SkillItem[]>([]);
  const [statusFilter, setStatusFilter] = useState<SkillStatusFilter>('all');
  const [sourceFilter, setSourceFilter] = useState<SkillSourceFilter>('all');
  const [keyword, setKeyword] = useState('');

  const sortedSkills = useMemo(
    () => [...skills].sort((left, right) => {
      const leftEnabled = enabledOf(left) ? 0 : 1;
      const rightEnabled = enabledOf(right) ? 0 : 1;
      if (leftEnabled !== rightEnabled) return leftEnabled - rightEnabled;
      const leftSource = isBuiltinSkill(left) ? 0 : 1;
      const rightSource = isBuiltinSkill(right) ? 0 : 1;
      if (leftSource !== rightSource) return leftSource - rightSource;
      return displaySkillName(left).localeCompare(displaySkillName(right));
    }),
    [skills],
  );

  const filteredSkills = useMemo(() => {
    const text = keyword.trim().toLowerCase();
    return sortedSkills.filter((skill) => {
      const enabled = enabledOf(skill);
      const matchesStatus = statusFilter === 'all'
        || (statusFilter === 'enabled' ? enabled : !enabled);
      const matchesSource = sourceFilter === 'all'
        || (sourceFilter === 'builtin' ? isBuiltinSkill(skill) : !isBuiltinSkill(skill));
      const matchesText = !text
        || displaySkillName(skill).toLowerCase().includes(text)
        || skill.name.toLowerCase().includes(text)
        || String(skill.description || '').toLowerCase().includes(text)
        || skillCategory(skill).toLowerCase().includes(text);
      return matchesStatus && matchesSource && matchesText;
    });
  }, [keyword, sortedSkills, sourceFilter, statusFilter]);

  const stats = useMemo(() => ({
    total: skills.length,
    enabled: skills.filter(enabledOf).length,
    builtin: skills.filter(isBuiltinSkill).length,
    custom: skills.filter((skill) => !isBuiltinSkill(skill)).length,
  }), [skills]);

  const load = async () => {
    setLoading(true);
    try {
      const data = await api.listSkills(scope);
      setSkills(data.skills || []);
    } finally {
      setLoading(false);
    }
  };

  const toggle = async (skill: SkillItem, checked: boolean) => {
    setSavingName(skill.name);
    try {
      await api.toggleSkill(scope, skill.name, checked ? 'open' : 'close');
      message.success(`${displaySkillName(skill)} 已${checked ? '启用' : '禁用'}`);
      await load();
    } finally {
      setSavingName('');
    }
  };

  const deleteSkill = async (skill: SkillItem) => {
    if (isBuiltinSkill(skill)) {
      message.warning('系统内置技能不能删除');
      return;
    }
    setDeletingName(skill.name);
    try {
      await api.deleteSkill(scope, skill.name);
      message.success(`${displaySkillName(skill)} 已删除`);
      await load();
    } finally {
      setDeletingName('');
    }
  };

  useEffect(() => {
    void load();
  }, [scope.agentId, scope.bindingId]);

  return (
    <div className="skills-page">
      <PageTitle
        title="技能库"
        description="管理当前员工可调用的技能能力，控制启用状态与本地技能边界。"
        extra={(
          <Space wrap>
            <Button icon={<ReloadOutlined />} onClick={() => void load()}>刷新</Button>
          </Space>
        )}
      />

      <div className="skills-overview-grid">
        <Card className="skills-overview-card">
          <Statistic title="全部技能" value={stats.total} loading={loading} />
        </Card>
        <Card className="skills-overview-card">
          <Statistic title="已启用" value={stats.enabled} loading={loading} />
        </Card>
        <Card className="skills-overview-card">
          <Statistic title="系统内置" value={stats.builtin} loading={loading} />
        </Card>
        <Card className="skills-overview-card">
          <Statistic title="本地技能" value={stats.custom} loading={loading} />
        </Card>
      </div>

      <div className="skills-toolbar">
        <Input
          allowClear
          prefix={<SearchOutlined />}
          placeholder="搜索技能名称、描述或分类"
          value={keyword}
          onChange={(event) => setKeyword(event.target.value)}
        />
        <Select<SkillStatusFilter>
          value={statusFilter}
          onChange={setStatusFilter}
          options={[
            { label: '全部状态', value: 'all' },
            { label: '已启用', value: 'enabled' },
            { label: '已停用', value: 'disabled' },
          ]}
        />
        <Select<SkillSourceFilter>
          value={sourceFilter}
          onChange={setSourceFilter}
          options={[
            { label: '全部来源', value: 'all' },
            { label: '系统内置', value: 'builtin' },
            { label: '本地技能', value: 'custom' },
          ]}
        />
      </div>

      {filteredSkills.length === 0 ? (
        <Card className="skills-empty-card" loading={loading}>
          {!loading ? (
            <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description={keyword ? '没有匹配的技能。' : '当前上下文还没有技能。'}>
              <Button icon={<ReloadOutlined />} onClick={() => void load()}>重新加载</Button>
            </Empty>
          ) : null}
        </Card>
      ) : (
        <div className="skills-card-grid">
          {filteredSkills.map((skill) => {
            const enabled = enabledOf(skill);
            return (
              <Card key={skill.name} className="skill-card" loading={loading}>
                <div className="skill-card-head">
                  <div className="skill-card-icon">
                    {isBuiltinSkill(skill) ? <SafetyCertificateOutlined /> : <CodeOutlined />}
                  </div>
                  <div className="skill-card-title">
                    <Space size={8} wrap>
                      <Typography.Title level={5} className="skill-card-name">
                        {displaySkillName(skill)}
                      </Typography.Title>
                      <Badge status={enabled ? 'success' : 'default'} text={enabled ? '已启用' : '已停用'} />
                    </Space>
                    <Typography.Text type="secondary">{skill.name}</Typography.Text>
                  </div>
                </div>
                <div className="skill-card-tags">
                  {sourceTag(skill)}
                  <Tag>{skillCategory(skill)}</Tag>
                  {skill.version ? <Tag>v{String(skill.version)}</Tag> : null}
                </div>
                <Typography.Paragraph className="skill-card-desc" type="secondary" ellipsis={{ rows: 2 }}>
                  {skill.description || '该技能未提供描述。'}
                </Typography.Paragraph>
                <div className="skill-card-footer">
                  <Typography.Text type="secondary">{sourceLabel(skill)}</Typography.Text>
                  <Space size={8}>
                    <Switch
                      checked={enabled}
                      loading={savingName === skill.name}
                      onChange={(checked) => void toggle(skill, checked)}
                    />
                    <Tooltip title={isBuiltinSkill(skill) ? '系统内置技能不可删除' : '删除技能'}>
                      <Popconfirm
                        title="确认删除该技能？"
                        onConfirm={() => void deleteSkill(skill)}
                        disabled={isBuiltinSkill(skill)}
                      >
                        <Button
                          danger
                          size="small"
                          icon={<DeleteOutlined />}
                          disabled={isBuiltinSkill(skill)}
                          loading={deletingName === skill.name}
                        />
                      </Popconfirm>
                    </Tooltip>
                  </Space>
                </div>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
