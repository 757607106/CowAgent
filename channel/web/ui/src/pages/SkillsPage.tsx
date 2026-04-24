import { Button, Card, Space, Switch, Table, Tag, message } from 'antd';
import { useEffect, useState } from 'react';
import { useRuntimeScope } from '../context/runtime';
import { PageTitle } from '../components/PageTitle';
import { api } from '../services/api';
import type { SkillItem } from '../types';

function enabledOf(skill: SkillItem): boolean {
  return Boolean(skill.enabled ?? skill.open ?? skill.active ?? skill.is_open);
}

export default function SkillsPage() {
  const { scope } = useRuntimeScope();
  const [loading, setLoading] = useState(false);
  const [savingName, setSavingName] = useState('');
  const [skills, setSkills] = useState<SkillItem[]>([]);

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
        dataSource={skills}
        pagination={{ pageSize: 20 }}
        columns={[
          { title: '技能', dataIndex: 'name' },
          { title: '描述', dataIndex: 'description', render: (v: string) => v || '-' },
          {
            title: '状态',
            render: (_, row) => (enabledOf(row) ? <Tag color="green">已启用</Tag> : <Tag>已禁用</Tag>),
          },
          {
            title: '操作',
            render: (_, row) => (
              <Switch
                checked={enabledOf(row)}
                loading={savingName === row.name}
                onChange={(checked) => void toggle(row, checked)}
              />
            ),
          },
        ]}
      />
      <Space style={{ marginTop: 12 }}>
        <span>共 {skills.length} 个技能</span>
      </Space>
    </Card>
  );
}
