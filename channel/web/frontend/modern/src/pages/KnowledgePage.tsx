import { XMarkdown } from '@ant-design/x-markdown';
import { Button, Card, Input, Space, Spin, Tabs, Tree, Typography } from 'antd';
import { useEffect, useMemo, useState } from 'react';
import type { DataNode } from 'antd/es/tree';
import { useRuntimeScope } from '../context/runtime';
import { JsonBlock } from '../components/JsonBlock';
import { PageTitle } from '../components/PageTitle';
import { api } from '../services/api';
import type { RuntimeScope } from '../types';

interface KnowledgeFile {
  name: string;
  title: string;
  size: number;
}

interface KnowledgeGroup {
  dir: string;
  files: KnowledgeFile[];
}

interface KnowledgeListResult {
  tree: KnowledgeGroup[];
  stats: { pages: number; size: number };
  enabled: boolean;
}

interface KnowledgePanelProps {
  scope: RuntimeScope;
  title?: string;
  description?: string;
  embedded?: boolean;
}

function formatBytes(size: number): string {
  if (!Number.isFinite(size) || size <= 0) return '0 B';
  if (size < 1024) return `${size} B`;
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
  return `${(size / (1024 * 1024)).toFixed(1)} MB`;
}

export function KnowledgePanel({
  scope,
  title = '知识库',
  description = '按目录浏览知识文档，阅读内容并查看知识图谱。',
  embedded = false,
}: KnowledgePanelProps) {
  const [tabKey, setTabKey] = useState<'docs' | 'graph'>('docs');
  const [loading, setLoading] = useState(false);
  const [listData, setListData] = useState<KnowledgeListResult>({
    tree: [],
    stats: { pages: 0, size: 0 },
    enabled: true,
  });
  const [search, setSearch] = useState('');

  const [selectedPath, setSelectedPath] = useState('');
  const [selectedTitle, setSelectedTitle] = useState('');
  const [contentLoading, setContentLoading] = useState(false);
  const [content, setContent] = useState('');

  const [graphLoading, setGraphLoading] = useState(false);
  const [graph, setGraph] = useState<Record<string, any> | null>(null);

  const loadList = async () => {
    setLoading(true);
    try {
      const data = await api.listKnowledge(scope);
      setListData({
        tree: (data.tree || []) as KnowledgeGroup[],
        stats: (data.stats || { pages: 0, size: 0 }) as { pages: number; size: number },
        enabled: Boolean(data.enabled ?? true),
      });
    } finally {
      setLoading(false);
    }
  };

  const readPath = async (path: string, title?: string) => {
    if (!path) return;
    setSelectedPath(path);
    setSelectedTitle(title || path);
    setContentLoading(true);
    try {
      const data = await api.readKnowledge(scope, path);
      setContent(String(data.content || ''));
    } finally {
      setContentLoading(false);
    }
  };

  const loadGraph = async () => {
    setGraphLoading(true);
    try {
      const data = await api.graphKnowledge(scope);
      setGraph(data);
    } finally {
      setGraphLoading(false);
    }
  };

  useEffect(() => {
    setSearch('');
    setSelectedPath('');
    setSelectedTitle('');
    setContent('');
    setGraph(null);
    setTabKey('docs');
    void loadList();
  }, [scope.tenantId, scope.agentId, scope.bindingId]);

  const treeData = useMemo<DataNode[]>(() => {
    const keyword = search.trim().toLowerCase();

    return listData.tree
      .map((group) => {
        const files = (group.files || []).filter((file) => {
          if (!keyword) return true;
          return file.name.toLowerCase().includes(keyword) || file.title.toLowerCase().includes(keyword);
        });

        if (files.length === 0 && keyword) {
          return null;
        }

        return {
          key: group.dir,
          title: `${group.dir} (${files.length})`,
          selectable: false,
          children: files.map((file) => ({
            key: `${group.dir}/${file.name}`,
            title: (
              <Space size={6}>
                <span>{file.title || file.name}</span>
                <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                  {formatBytes(file.size)}
                </Typography.Text>
              </Space>
            ),
            isLeaf: true,
          })),
        } satisfies DataNode;
      })
      .filter(Boolean) as DataNode[];
  }, [listData.tree, search]);

  return (
    <Card className={embedded ? 'knowledge-embedded-card' : undefined}>
      <PageTitle
        title={title}
        description={description}
        extra={(
          <Button onClick={() => void loadList()}>刷新</Button>
        )}
      />

      <Tabs
        activeKey={tabKey}
        onChange={(value) => {
          const next = value as 'docs' | 'graph';
          setTabKey(next);
          if (next === 'graph' && graph === null) {
            void loadGraph();
          }
        }}
        items={[
          {
            key: 'docs',
            label: '文档',
            children: (
              <Space className="knowledge-doc-layout" align="start" style={{ width: '100%' }} size={12}>
                <Card className="knowledge-tree-card">
                  <Space direction="vertical" style={{ width: '100%' }} size={10}>
                    <Typography.Text type="secondary">
                      {listData.enabled
                        ? `${listData.stats.pages} 篇文档 · ${formatBytes(listData.stats.size)}`
                        : '当前智能体未启用知识库'}
                    </Typography.Text>
                    <Input.Search
                      allowClear
                      placeholder="搜索标题或文件名"
                      value={search}
                      onChange={(event) => setSearch(event.target.value)}
                    />
                    {loading ? (
                      <Spin />
                    ) : (
                      <Tree
                        treeData={treeData}
                        defaultExpandAll
                        selectedKeys={selectedPath ? [selectedPath] : []}
                        onSelect={(keys) => {
                          const key = String(keys[0] || '');
                          if (!key || !key.includes('/')) return;
                          void readPath(key, key.split('/').pop() || key);
                        }}
                      />
                    )}
                  </Space>
                </Card>

                <Card
                  title={selectedPath ? `文档：${selectedTitle}` : '文档内容'}
                  extra={selectedPath ? <Typography.Text type="secondary">{selectedPath}</Typography.Text> : null}
                  style={{ flex: 1, minHeight: 620 }}
                >
                  {contentLoading ? (
                    <Spin />
                  ) : content ? (
                    <XMarkdown content={content} rootClassName="chat-markdown" openLinksInNewTab escapeRawHtml />
                  ) : (
                    <Typography.Text type="secondary">请选择左侧文档查看内容。</Typography.Text>
                  )}
                </Card>
              </Space>
            ),
          },
          {
            key: 'graph',
            label: '图谱',
            children: (
              <Card
                extra={<Button loading={graphLoading} onClick={() => void loadGraph()}>刷新图谱</Button>}
              >
                {graphLoading ? (
                  <Spin />
                ) : (
                  <>
                    <Space size={16} style={{ marginBottom: 12 }}>
                      <Typography.Text>节点：{(graph?.nodes || []).length}</Typography.Text>
                      <Typography.Text>关系：{(graph?.links || []).length}</Typography.Text>
                      <Typography.Text type="secondary">状态：{String(graph?.enabled ?? true)}</Typography.Text>
                    </Space>
                    <JsonBlock value={graph || { nodes: [], links: [] }} style={{ maxHeight: 560 }} />
                  </>
                )}
              </Card>
            ),
          },
        ]}
      />
    </Card>
  );
}

export default function KnowledgePage() {
  const { scope } = useRuntimeScope();
  return <KnowledgePanel scope={scope} />;
}
