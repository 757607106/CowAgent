import { XMarkdown } from '@ant-design/x-markdown';
import { Button, Card, Segmented, Space, Spin, Table, Tag, Typography } from 'antd';
import { useEffect, useMemo, useState } from 'react';
import type { ColumnsType } from 'antd/es/table';
import { useRuntimeScope } from '../context/runtime';
import { PageTitle } from '../components/PageTitle';
import { api } from '../services/api';

type MemoryCategory = 'memory' | 'dream';

interface MemoryFileItem {
  filename: string;
  type: 'global' | 'daily' | 'dream' | string;
  size: number;
  updated_at: string;
}

const PAGE_SIZE = 20;

function formatBytes(size: number): string {
  if (!Number.isFinite(size) || size <= 0) return '0 B';
  if (size < 1024) return `${size} B`;
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
  return `${(size / (1024 * 1024)).toFixed(1)} MB`;
}

function typeTag(type: string) {
  if (type === 'global') return <Tag color="blue">Global</Tag>;
  if (type === 'dream') return <Tag color="purple">Dream</Tag>;
  if (type === 'daily') return <Tag color="cyan">Daily</Tag>;
  return <Tag>{type || '-'}</Tag>;
}

export default function MemoryPage() {
  const { scope } = useRuntimeScope();
  const [category, setCategory] = useState<MemoryCategory>('memory');
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [files, setFiles] = useState<MemoryFileItem[]>([]);
  const [selected, setSelected] = useState<string>('');
  const [contentLoading, setContentLoading] = useState(false);
  const [content, setContent] = useState('');

  const columns = useMemo<ColumnsType<MemoryFileItem>>(() => ([
    {
      title: '文件名',
      dataIndex: 'filename',
      width: '46%',
      render: (value: string) => <Typography.Text ellipsis>{value}</Typography.Text>,
    },
    {
      title: '类型',
      dataIndex: 'type',
      width: 120,
      render: (value: string) => typeTag(value),
    },
    {
      title: '大小',
      dataIndex: 'size',
      width: 120,
      render: (value: number) => formatBytes(Number(value || 0)),
    },
    {
      title: '更新时间',
      dataIndex: 'updated_at',
      width: 180,
      render: (value: string) => value || '-',
    },
  ]), []);

  const loadFiles = async (targetPage = 1) => {
    setLoading(true);
    try {
      const data = await api.listMemory(scope, category, targetPage, PAGE_SIZE);
      const nextList = (data.list || data.files || data.items || []) as MemoryFileItem[];
      setFiles(nextList);
      setTotal(Number(data.total || nextList.length || 0));
      setPage(Number(data.page || targetPage));
    } finally {
      setLoading(false);
    }
  };

  const loadContent = async (filename: string) => {
    setSelected(filename);
    setContentLoading(true);
    try {
      const data = await api.memoryContent(scope, filename, category);
      setContent(String(data.content || ''));
    } finally {
      setContentLoading(false);
    }
  };

  useEffect(() => {
    setSelected('');
    setContent('');
    void loadFiles(1);
  }, [category, scope.agentId, scope.bindingId]);

  return (
    <Card>
      <PageTitle
        title="记忆管理"
        description="查看记忆文件与梦境日记，支持分页与内容阅读。"
        extra={(
          <Space>
            <Segmented
              options={[
                { label: '记忆文件', value: 'memory' },
                { label: '梦境日记', value: 'dream' },
              ]}
              value={category}
              onChange={(value) => setCategory(value as MemoryCategory)}
            />
            <Button onClick={() => void loadFiles(page)}>刷新</Button>
          </Space>
        )}
      />

      <Space align="start" style={{ width: '100%' }} size={12}>
        <Card title="文件列表" style={{ width: 620 }} bodyStyle={{ padding: 0 }}>
          <Table<MemoryFileItem>
            rowKey={(row) => row.filename}
            loading={loading}
            size="small"
            columns={columns}
            dataSource={files}
            pagination={{
              current: page,
              pageSize: PAGE_SIZE,
              total,
              showSizeChanger: false,
              showTotal: (value) => `共 ${value} 条`,
              onChange: (targetPage) => {
                void loadFiles(targetPage);
              },
            }}
            onRow={(row) => ({
              onClick: () => {
                void loadContent(row.filename);
              },
              style: {
                cursor: 'pointer',
                background: selected === row.filename ? '#f0f5ff' : undefined,
              },
            })}
          />
        </Card>

        <Card
          title={selected ? `内容：${selected}` : '内容预览'}
          style={{ flex: 1, minHeight: 540 }}
        >
          {contentLoading ? (
            <Spin />
          ) : content ? (
            <XMarkdown content={content} rootClassName="chat-markdown" openLinksInNewTab escapeRawHtml />
          ) : (
            <Typography.Text type="secondary">请选择左侧文件查看内容。</Typography.Text>
          )}
        </Card>
      </Space>
    </Card>
  );
}
