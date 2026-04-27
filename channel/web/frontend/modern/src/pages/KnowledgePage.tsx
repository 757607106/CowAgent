import { XMarkdown } from '@ant-design/x-markdown';
import * as d3 from 'd3';
import { Button, Card, Empty, Input, Space, Spin, Tabs, Tree, Typography } from 'antd';
import { useEffect, useMemo, useRef, useState } from 'react';
import type { DataNode } from 'antd/es/tree';
import { useRuntimeScope } from '../context/runtime';
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

interface KnowledgeGraphNode {
  id: string;
  label: string;
  category: string;
}

interface KnowledgeGraphLink {
  source: string;
  target: string;
  label?: string;
}

interface KnowledgeGraphSimulationNode extends KnowledgeGraphNode, d3.SimulationNodeDatum {}

interface KnowledgeGraphSimulationLink extends d3.SimulationLinkDatum<KnowledgeGraphSimulationNode> {
  source: string | KnowledgeGraphSimulationNode;
  target: string | KnowledgeGraphSimulationNode;
  label?: string;
}

function formatBytes(size: number): string {
  if (!Number.isFinite(size) || size <= 0) return '0 B';
  if (size < 1024) return `${size} B`;
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
  return `${(size / (1024 * 1024)).toFixed(1)} MB`;
}

function asString(value: unknown): string {
  return typeof value === 'string' ? value.trim() : '';
}

function graphEndpointId(value: unknown): string {
  if (typeof value === 'string') return value.trim();
  if (value && typeof value === 'object') {
    return asString((value as Record<string, unknown>).id);
  }
  return '';
}

function getGraphNodes(graph: Record<string, any> | null): KnowledgeGraphNode[] {
  const rawNodes = Array.isArray(graph?.nodes) ? graph.nodes : [];
  return rawNodes.flatMap((item) => {
    if (!item || typeof item !== 'object') return [];
    const source = item as Record<string, unknown>;
    const id = asString(source.id);
    if (!id) return [];
    return [{
      id,
      label: asString(source.label) || id,
      category: asString(source.category) || 'root',
    }];
  });
}

function getGraphLinks(graph: Record<string, any> | null): KnowledgeGraphLink[] {
  const rawLinks = Array.isArray(graph?.links)
    ? graph.links
    : (Array.isArray(graph?.edges) ? graph.edges : []);
  return rawLinks.flatMap((item) => {
    if (!item || typeof item !== 'object') return [];
    const source = item as Record<string, unknown>;
    const sourceId = graphEndpointId(source.source);
    const targetId = graphEndpointId(source.target);
    if (!sourceId || !targetId) return [];
    return [{
      source: sourceId,
      target: targetId,
      label: asString(source.label) || asString(source.relation) || asString(source.type),
    }];
  });
}

function shortLabel(label: string): string {
  return label.length > 15 ? `${label.slice(0, 14)}…` : label;
}

function KnowledgeGraphView({
  graph,
  onOpenNode,
}: {
  graph: Record<string, any> | null;
  onOpenNode: (node: KnowledgeGraphNode) => void;
}) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const openNodeRef = useRef(onOpenNode);
  const nodes = useMemo(() => getGraphNodes(graph), [graph]);
  const links = useMemo(() => {
    const nodeIds = new Set(nodes.map((node) => node.id));
    return getGraphLinks(graph).filter((link) => nodeIds.has(link.source) && nodeIds.has(link.target));
  }, [graph, nodes]);

  useEffect(() => {
    openNodeRef.current = onOpenNode;
  }, [onOpenNode]);

  useEffect(() => {
    const container = containerRef.current;
    if (!container || nodes.length === 0) return undefined;

    container.innerHTML = '';
    container.style.position = 'relative';

    const width = container.clientWidth || 960;
    const height = container.clientHeight || 600;
    const graphNodes: KnowledgeGraphSimulationNode[] = nodes.map((node) => ({ ...node }));
    const graphLinks: KnowledgeGraphSimulationLink[] = links.map((link) => ({ ...link }));
    const categories = Array.from(new Set(graphNodes.map((node) => node.category)));
    const colorScale = d3.scaleOrdinal<string, string>(d3.schemeTableau10).domain(categories);

    const connCount: Record<string, number> = {};
    graphNodes.forEach((node) => {
      connCount[node.id] = 0;
    });
    graphLinks.forEach((link) => {
      const sourceId = graphEndpointId(link.source);
      const targetId = graphEndpointId(link.target);
      connCount[sourceId] = (connCount[sourceId] || 0) + 1;
      connCount[targetId] = (connCount[targetId] || 0) + 1;
    });

    const getNodeRadius = (node: KnowledgeGraphSimulationNode) => Math.max(5, Math.min(16, 5 + (connCount[node.id] || 0) * 2));

    const svg = d3.select(container)
      .append('svg')
      .attr('width', width)
      .attr('height', height)
      .attr('class', 'knowledge-graph-svg')
      .attr('role', 'img')
      .attr('aria-label', '知识图谱关系');

    const g = svg.append('g');
    let currentZoomScale = 1;
    let label: d3.Selection<SVGTextElement, KnowledgeGraphSimulationNode, SVGGElement, unknown> | null = null;

    const updateLabelVisibility = () => {
      if (!label) return;
      if (currentZoomScale < 0.8) {
        label.attr('opacity', 0);
      } else {
        const baseFontSize = Math.min(12, 10 / Math.max(currentZoomScale * 0.7, 0.5));
        label.attr('opacity', 1).attr('font-size', baseFontSize);
      }
    };

    const zoom = d3.zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.2, 5])
      .on('zoom', (event) => {
        g.attr('transform', event.transform.toString());
        currentZoomScale = event.transform.k;
        updateLabelVisibility();
      });
    svg.call(zoom);

    const simulation = d3.forceSimulation<KnowledgeGraphSimulationNode>(graphNodes)
      .force('link', d3.forceLink<KnowledgeGraphSimulationNode, KnowledgeGraphSimulationLink>(graphLinks).id((node) => node.id).distance(90))
      .force('charge', d3.forceManyBody<KnowledgeGraphSimulationNode>().strength(-180))
      .force('center', d3.forceCenter(width / 2, height / 2))
      .force('x', d3.forceX<KnowledgeGraphSimulationNode>(width / 2).strength(0.06))
      .force('y', d3.forceY<KnowledgeGraphSimulationNode>(height / 2).strength(0.06))
      .force('collision', d3.forceCollide<KnowledgeGraphSimulationNode>().radius((node) => getNodeRadius(node) + 30));

    const link = g.append('g')
      .selectAll<SVGLineElement, KnowledgeGraphSimulationLink>('line')
      .data(graphLinks)
      .join('line')
      .attr('stroke', '#94a3b8')
      .attr('stroke-opacity', 0.3)
      .attr('stroke-width', 1);

    const drag = d3.drag<SVGCircleElement, KnowledgeGraphSimulationNode>()
      .on('start', (event, node) => {
        if (!event.active) simulation.alphaTarget(0.3).restart();
        node.fx = node.x;
        node.fy = node.y;
      })
      .on('drag', (event, node) => {
        node.fx = event.x;
        node.fy = event.y;
      })
      .on('end', (event, node) => {
        if (!event.active) simulation.alphaTarget(0);
        node.fx = null;
        node.fy = null;
      });

    const node = g.append('g')
      .selectAll<SVGCircleElement, KnowledgeGraphSimulationNode>('circle')
      .data(graphNodes)
      .join('circle')
      .attr('r', (item) => getNodeRadius(item))
      .attr('fill', (item) => colorScale(item.category))
      .attr('stroke', '#fff')
      .attr('stroke-width', 1.5)
      .style('cursor', 'pointer')
      .call(drag);

    label = g.append('g')
      .selectAll<SVGTextElement, KnowledgeGraphSimulationNode>('text')
      .data(graphNodes)
      .join('text')
      .text((item) => shortLabel(item.label))
      .attr('font-size', 9)
      .attr('dx', (item) => getNodeRadius(item) + 4)
      .attr('dy', 3)
      .attr('fill', '#64748b')
      .style('pointer-events', 'none');

    const tooltip = document.createElement('div');
    tooltip.className = 'knowledge-graph-tooltip';
    container.appendChild(tooltip);

    const linkTouchesNode = (item: KnowledgeGraphSimulationLink, nodeId: string) => (
      graphEndpointId(item.source) === nodeId || graphEndpointId(item.target) === nodeId
    );
    const isConnectedNode = (targetNodeId: string, sourceNodeId: string) => (
      targetNodeId === sourceNodeId || graphLinks.some((item) => {
        const sourceId = graphEndpointId(item.source);
        const targetId = graphEndpointId(item.target);
        return (sourceId === sourceNodeId && targetId === targetNodeId)
          || (targetId === sourceNodeId && sourceId === targetNodeId);
      })
    );

    node.on('mouseover', (event, item) => {
      const [x, y] = d3.pointer(event, container);
      tooltip.textContent = `${item.label} (${item.category})`;
      tooltip.style.opacity = '1';
      tooltip.style.left = `${x + 12}px`;
      tooltip.style.top = `${y - 8}px`;
      link.attr('stroke-opacity', (linkItem) => (linkTouchesNode(linkItem, item.id) ? 0.8 : 0.1));
      node.attr('opacity', (nodeItem) => (isConnectedNode(nodeItem.id, item.id) ? 1 : 0.2));
      label?.attr('opacity', (nodeItem) => (isConnectedNode(nodeItem.id, item.id) ? 1 : 0.1));
    }).on('mousemove', (event) => {
      const [x, y] = d3.pointer(event, container);
      tooltip.style.left = `${x + 12}px`;
      tooltip.style.top = `${y - 8}px`;
    }).on('mouseout', () => {
      tooltip.style.opacity = '0';
      link.attr('stroke-opacity', 0.3);
      node.attr('opacity', 1);
      label?.attr('opacity', 1);
    }).on('click', (_event, item) => {
      openNodeRef.current({
        id: item.id,
        label: item.label,
        category: item.category,
      });
    });

    simulation.on('tick', () => {
      link
        .attr('x1', (item) => (item.source as KnowledgeGraphSimulationNode).x || 0)
        .attr('y1', (item) => (item.source as KnowledgeGraphSimulationNode).y || 0)
        .attr('x2', (item) => (item.target as KnowledgeGraphSimulationNode).x || 0)
        .attr('y2', (item) => (item.target as KnowledgeGraphSimulationNode).y || 0);
      node.attr('cx', (item) => item.x || 0).attr('cy', (item) => item.y || 0);
      label?.attr('x', (item) => item.x || 0).attr('y', (item) => item.y || 0);
    });

    simulation.on('end', () => {
      const pad = 16;
      let x0 = Infinity;
      let y0 = Infinity;
      let x1 = -Infinity;
      let y1 = -Infinity;
      graphNodes.forEach((item) => {
        const x = item.x || width / 2;
        const y = item.y || height / 2;
        if (x < x0) x0 = x;
        if (y < y0) y0 = y;
        if (x > x1) x1 = x;
        if (y > y1) y1 = y;
      });
      const boundsWidth = x1 - x0 + pad * 2;
      const boundsHeight = y1 - y0 + pad * 2;
      if (boundsWidth > 0 && boundsHeight > 0) {
        const scale = Math.min(width / boundsWidth, height / boundsHeight, 4);
        const tx = width / 2 - ((x0 + x1) / 2) * scale;
        const ty = height / 2 - ((y0 + y1) / 2) * scale;
        svg.transition().duration(500).call(
          zoom.transform,
          d3.zoomIdentity.translate(tx, ty).scale(scale),
        );
      }
    });

    const legend = document.createElement('div');
    legend.className = 'knowledge-graph-legend';
    categories.forEach((category) => {
      const item = document.createElement('span');
      item.className = 'knowledge-graph-legend-item';
      const dot = document.createElement('span');
      dot.className = 'knowledge-graph-legend-dot';
      dot.style.background = colorScale(category);
      item.appendChild(dot);
      item.appendChild(document.createTextNode(category));
      legend.appendChild(item);
    });
    container.appendChild(legend);

    return () => {
      simulation.stop();
      container.innerHTML = '';
    };
  }, [links, nodes]);

  if (nodes.length === 0) {
    return (
      <div className="knowledge-graph-empty">
        <Empty description="暂无知识图谱" />
      </div>
    );
  }

  return <div ref={containerRef} className="knowledge-graph-view" />;
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
  const graphNodes = useMemo(() => getGraphNodes(graph), [graph]);
  const graphLinks = useMemo(() => getGraphLinks(graph), [graph]);

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
                <Typography.Text type="secondary" className="knowledge-file-size">
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
              <div className="knowledge-doc-layout">
                <Card className="knowledge-tree-card">
                  <Space vertical className="full-width-stack" size={10}>
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
                          const slashIndex = key.lastIndexOf('/');
                          void readPath(key, slashIndex >= 0 ? key.slice(slashIndex + 1) : key);
                        }}
                      />
                    )}
                  </Space>
                </Card>

                <Card
                  title={selectedPath ? `文档：${selectedTitle}` : '文档内容'}
                  extra={selectedPath ? <Typography.Text type="secondary">{selectedPath}</Typography.Text> : null}
                  className="knowledge-content-card"
                >
                  {contentLoading ? (
                    <Spin />
                  ) : content ? (
                    <XMarkdown content={content} rootClassName="chat-markdown" openLinksInNewTab escapeRawHtml />
                  ) : (
                    <Typography.Text type="secondary">请选择左侧文档查看内容。</Typography.Text>
                  )}
                </Card>
              </div>
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
                    <Space size={16} className="knowledge-graph-meta">
                      <Typography.Text>节点：{graphNodes.length}</Typography.Text>
                      <Typography.Text>关系：{graphLinks.length}</Typography.Text>
                      <Typography.Text type="secondary">状态：{String(graph?.enabled ?? true)}</Typography.Text>
                    </Space>
                    <KnowledgeGraphView
                      graph={graph}
                      onOpenNode={(node) => {
                        setTabKey('docs');
                        void readPath(node.id, node.label);
                      }}
                    />
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
