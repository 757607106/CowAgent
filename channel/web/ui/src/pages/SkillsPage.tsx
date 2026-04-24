import { DeleteOutlined } from '@ant-design/icons';
import { Button, Card, Popconfirm, Space, Switch, Table, Tag, message } from 'antd';
import { useEffect, useMemo, useState } from 'react';
import { useRuntimeScope } from '../context/runtime';
import { PageTitle } from '../components/PageTitle';
import { api } from '../services/api';
import type { SkillItem } from '../types';

function enabledOf(skill: SkillItem): boolean {
  return Boolean(skill.enabled ?? skill.open ?? skill.active ?? skill.is_open);
}

function isBuiltinSkill(skill: SkillItem): boolean {
  return skill.source === 'builtin';
}

function sourceTag(skill: SkillItem) {
  if (isBuiltinSkill(skill)) return <Tag color="blue">内置</Tag>;
  return <Tag color="green">非内置</Tag>;
}

export default function SkillsPage() {
  const { scope } = useRuntimeScope();
  const [loading, setLoading] = useState(false);
  const [savingName, setSavingName] = useState('');
  const [deletingName, setDeletingName] = useState('');
  const [skills, setSkills] = useState<SkillItem[]>([]);

  const sortedSkills = useMemo(
    () => [...skills].sort((left, right) => {
      const leftSource = isBuiltinSkill(left) ? 0 : 1;
      const rightSource = isBuiltinSkill(right) ? 0 : 1;
      if (leftSource !== rightSource) return leftSource - rightSource;
      return left.name.localeCompare(right.name);
    }),
    [skills],
  );

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
      message.success(`${skill.name} 已${checked ? '启用' : '禁用'}`);
      await load();
    } finally {
      setSavingName('');
    }
  };

  const deleteSkill = async (skill: SkillItem) => {
    if (isBuiltinSkill(skill)) {
      message.warning('内置技能不能删除');
      return;
    }
    setDeletingName(skill.name);
    try {
      await api.deleteSkill(scope, skill.name);
      message.success(`${skill.name} 已删除`);
      await load();
    } finally {
      setDeletingName('');
    }
  };

  useEffect(() => {
    void load();
  }, [scope.agentId, scope.bindingId]);

  return (
    <Card>
      <PageTitle
        title="技能管理"
        description="按当前运行上下文查看并启停技能。"
        extra={<Button onClick={() => void load()}>刷新</Button>}
      />
      <Table<SkillItem>
        rowKey={(row) => row.name}
        loading={loading}
        dataSource={sortedSkills}
        pagination={{ pageSize: 20 }}
        columns={[
          {
            title: '技能',
            dataIndex: 'name',
            render: (value: string, row) => row.display_name || value,
          },
          {
            title: '来源',
            dataIndex: 'source',
            width: 120,
            render: (_, row) => sourceTag(row),
            filters: [
              { text: '内置', value: 'builtin' },
              { text: '非内置', value: 'custom' },
            ],
            onFilter: (value, row) => (value === 'builtin' ? isBuiltinSkill(row) : !isBuiltinSkill(row)),
          },
          { title: '描述', dataIndex: 'description', render: (v: string) => v || '-' },
          {
            title: '状态',
            width: 120,
            render: (_, row) => (enabledOf(row) ? <Tag color="green">已启用</Tag> : <Tag>已禁用</Tag>),
          },
          {
            title: '操作',
            width: 180,
            render: (_, row) => (
              <Space>
                <Switch
                  checked={enabledOf(row)}
                  loading={savingName === row.name}
                  onChange={(checked) => void toggle(row, checked)}
                />
                <Popconfirm
                  title={isBuiltinSkill(row) ? '内置技能不能删除' : '确认删除该技能？'}
                  onConfirm={() => void deleteSkill(row)}
                  disabled={isBuiltinSkill(row)}
                >
                  <Button
                    danger
                    size="small"
                    icon={<DeleteOutlined />}
                    disabled={isBuiltinSkill(row)}
                    loading={deletingName === row.name}
                  >
                    删除
                  </Button>
                </Popconfirm>
              </Space>
            ),
          },
        ]}
      />
      <Space style={{ marginTop: 12 }}>
        <span>共 {skills.length} 个技能</span>
        <Tag color="blue">内置 {skills.filter(isBuiltinSkill).length}</Tag>
        <Tag color="green">非内置 {skills.filter((skill) => !isBuiltinSkill(skill)).length}</Tag>
      </Space>
    </Card>
  );
}
