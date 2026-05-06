import { XMarkdown } from '@ant-design/x-markdown';
import { Button, Card, Input, Segmented, Space, Spin, Tag, Typography } from 'antd';
import { useEffect, useMemo, useState } from 'react';
import type { ColumnsType } from 'antd/es/table';
import { PageTitle } from '../components/PageTitle';
import { DataTableShell } from '../components/console';
import { api } from '../services/api';
import type { RuntimeScope } from '../types';
import { formatBytes } from '../utils/format';

type MemoryCategory = 'memory' | 'dream';

interface MemoryFileItem {
  filename: string;
  type: 'global' | 'daily' | 'dream' | string;
  size: number;
  updated_at: string;
}

const PAGE_SIZE = 20;

interface MemoryPanelProps {
  scope: RuntimeScope;
  title?: string;
  description?: string;
  embedded?: boolean;
}

function typeTag(type: string) {
  if (type === 'global') return <Tag color="blue">Global</Tag>;
  if (type === 'dream') return <Tag color="purple">Dream</Tag>;
  if (type === 'daily') return <Tag color="cyan">Daily</Tag>;
  return <Tag>{type || '-'}</Tag>;
}

export function MemoryPanel({
  scope,
  title = '记忆管理',
  description = '查看记忆文件与梦境日记，支持分页与内容阅读。',
  embedded = false,
}: MemoryPanelProps) {
  const [category, setCategory] = useState<MemoryCategory>('memory');
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [files, setFiles] = useState<MemoryFileItem[]>([]);
  const [search, setSearch] = useState('');
  const [selected, setSelected] = useState<string>('');
  const [selectedItem, setSelectedItem] = useState<MemoryFileItem | null>(null);
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

  const loadContent = async (item: MemoryFileItem) => {
    setSelected(item.filename);
    setSelectedItem(item);
    setContentLoading(true);
    try {
      const data = await api.memoryContent(scope, item.filename, category);
      setContent(String(data.content || ''));
    } finally {
      setContentLoading(false);
    }
  };

  const filteredFiles = useMemo(() => {
    const keyword = search.trim().toLowerCase();
    if (!keyword) return files;
    return files.filter((item) => (
      item.filename.toLowerCase().includes(keyword)
      || String(item.type || '').toLowerCase().includes(keyword)
    ));
  }, [files, search]);

  const emptyState = useMemo(() => {
    const keyword = search.trim();
    if (keyword) {
      return {
        title: '未找到匹配文件',
        description: '请尝试更换关键词。',
        action: <Button onClick={() => setSearch('')}>清除筛选</Button>,
      };
    }
    return {
      title: category === 'dream' ? '暂无梦境日记' : '暂无记忆文件',
      description: '生成后会自动出现在这里。',
      action: <Button onClick={() => void loadFiles(page)}>刷新</Button>,
    };
  }, [category, loadFiles, page, search]);

  useEffect(() => {
    setSearch('');
    setSelected('');
    setSelectedItem(null);
    setContent('');
    void loadFiles(1);
  }, [category, scope.tenantId, scope.agentId, scope.bindingId]);

  return (
    <Card className={embedded ? 'memory-embedded-card' : undefined}>
      <PageTitle
        title={title}
        description={description}
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
            <Input.Search
              allowClear
              placeholder="筛选文件名"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              style={{ width: 220 }}
            />
            {search.trim() ? <Tag color="blue">本页筛选</Tag> : null}
            <Button onClick={() => void loadFiles(page)}>刷新</Button>
          </Space>
        )}
      />

      <div className="memory-panel-layout">
        <DataTableShell<MemoryFileItem>
          title="文件列表"
          compact
          className="memory-file-list-card memory-file-table-card"
          rowKey={(row) => row.filename}
          loading={loading}
          columns={columns}
          dataSource={filteredFiles}
          emptyState={emptyState}
          pagination={search.trim()
            ? false
            : {
              current: page,
              pageSize: PAGE_SIZE,
              total,
              showSizeChanger: false,
              showTotal: (value) => `共 ${value} 条`,
              onChange: (targetPage) => {
                void loadFiles(targetPage);
              },
            }}
          rowClassName={(row) => (selected === row.filename ? 'memory-row-selected' : '')}
          onRow={(row) => ({
            onClick: () => {
              void loadContent(row);
            },
          })}
        />

        <Card
          title={selected ? `内容：${selected}` : '内容预览'}
          extra={selectedItem ? (
            <Space size={6} wrap>
              {typeTag(selectedItem.type)}
              <Tag>{formatBytes(Number(selectedItem.size || 0))}</Tag>
              <Tag>{selectedItem.updated_at || '-'}</Tag>
            </Space>
          ) : null}
          className="memory-content-card"
        >
          {contentLoading ? (
            <Spin />
          ) : content ? (
            <XMarkdown content={content} rootClassName="chat-markdown" openLinksInNewTab escapeRawHtml />
          ) : (
            <Typography.Text type="secondary">请选择左侧文件查看内容。</Typography.Text>
          )}
        </Card>
      </div>
    </Card>
  );
}
