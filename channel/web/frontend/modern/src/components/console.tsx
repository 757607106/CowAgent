import { Card, Collapse, Empty, Table, Tag, Typography, type TableProps } from 'antd';
import type { ReactNode } from 'react';
import { JsonBlock } from './JsonBlock';
import { PageHeader } from './PageHeader';
import { Toolbar } from './Toolbar';
import { Workspace } from './Workspace';

type Tone = 'default' | 'success' | 'processing' | 'warning' | 'error' | 'disabled';

interface ConsolePageProps {
  title: ReactNode;
  description?: string;
  actions?: ReactNode;
  children: ReactNode;
  className?: string;
}

interface PageToolbarProps {
  children: ReactNode;
  align?: 'start' | 'end';
}

interface DataTableShellProps<T extends object> extends Omit<TableProps<T>, 'title'> {
  title?: ReactNode;
  toolbar?: ReactNode;
  compact?: boolean;
  emptyState?: {
    title?: ReactNode;
    description?: ReactNode;
    action?: ReactNode;
  };
}

interface EntityDetailLayoutProps {
  master: ReactNode;
  detail: ReactNode;
  className?: string;
}

interface AdvancedJsonPanelProps {
  title?: string;
  value: unknown;
  defaultOpen?: boolean;
}

interface StatusTagProps {
  status?: string | boolean | null;
  children?: ReactNode;
}

function toneForStatus(status: string | boolean | null | undefined): Tone {
  if (status === true) return 'success';
  if (status === false) return 'disabled';
  const normalized = String(status || '').toLowerCase();
  if (['active', 'enabled', 'success', 'ok', 'online', 'running'].includes(normalized)) return 'success';
  if (['processing', 'pending', 'loading'].includes(normalized)) return 'processing';
  if (['warning', 'disabled', 'inactive', 'stopped'].includes(normalized)) return 'warning';
  if (['error', 'failed', 'deleted'].includes(normalized)) return 'error';
  return 'default';
}

function colorForTone(tone: Tone) {
  if (tone === 'success') return 'green';
  if (tone === 'processing') return 'blue';
  if (tone === 'warning') return 'gold';
  if (tone === 'error') return 'red';
  if (tone === 'disabled') return 'default';
  return undefined;
}

export function ConsolePage({ title, description, actions, children, className }: ConsolePageProps) {
  return (
    <Workspace variant="console" className={className}>
      <PageHeader title={title} description={description} extra={actions} />
      {children}
    </Workspace>
  );
}

export function PageToolbar({ children, align = 'end' }: PageToolbarProps) {
  return <Toolbar align={align} ariaLabel="页面操作">{children}</Toolbar>;
}

function fallbackRowKey<T extends object>(record: T, index?: number) {
  const source = record as Record<string, unknown>;
  const key = source.id ?? source.key ?? source.agent_id ?? source.tenant_id ?? source.user_id ?? source.name ?? index;
  return typeof key === 'string' || typeof key === 'number' ? key : String(index ?? 0);
}

export function DataTableShell<T extends object>({
  title,
  toolbar,
  compact,
  className,
  rowKey,
  emptyState,
  ...tableProps
}: DataTableShellProps<T>) {
  const dataCount = Array.isArray(tableProps.dataSource) ? tableProps.dataSource.length : undefined;
  const hasRows = typeof dataCount === 'number' ? dataCount > 0 : true;
  let normalizedScroll = tableProps.scroll;

  if (!hasRows && normalizedScroll?.x === 'max-content') {
    const restScroll = { ...normalizedScroll };
    delete restScroll.x;
    normalizedScroll = Object.keys(restScroll).length > 0 ? restScroll : undefined;
  }

  const localeEmptyText = tableProps.locale?.emptyText;
  const emptyTitle = emptyState?.title ?? (typeof localeEmptyText === 'function' ? undefined : localeEmptyText) ?? '暂无数据';
  const emptyDescription = emptyState?.description ?? '调整筛选条件或完成创建后，数据会显示在这里。';
  const locale = {
    ...tableProps.locale,
    emptyText: (
      <Empty
        image={Empty.PRESENTED_IMAGE_SIMPLE}
        className="data-table-empty"
        description={(
          <span className="data-table-empty-copy">
            <Typography.Text strong>{emptyTitle}</Typography.Text>
            <Typography.Text type="secondary">{emptyDescription}</Typography.Text>
          </span>
        )}
      >
        {emptyState?.action}
      </Empty>
    ),
  };

  return (
    <Card className={['data-table-shell', compact ? 'data-table-shell-compact' : '', className].filter(Boolean).join(' ')}>
      {title || toolbar ? (
        <div className="data-table-shell-head">
          <div className="data-table-shell-title">{title}</div>
          {toolbar}
        </div>
      ) : null}
      <Table<T>
        rowKey={rowKey ?? fallbackRowKey}
        size={compact ? 'small' : undefined}
        {...tableProps}
        locale={locale}
        scroll={normalizedScroll}
      />
    </Card>
  );
}

export function EntityDetailLayout({ master, detail, className }: EntityDetailLayoutProps) {
  return (
    <div className={['entity-detail-layout', className].filter(Boolean).join(' ')}>
      <aside className="entity-detail-master">{master}</aside>
      <main className="entity-detail-main">{detail}</main>
    </div>
  );
}

export function AdvancedJsonPanel({ title = '高级信息', value, defaultOpen = false }: AdvancedJsonPanelProps) {
  return (
    <Collapse
      className="advanced-json-panel"
      ghost
      defaultActiveKey={defaultOpen ? ['raw'] : undefined}
      items={[
        {
          key: 'raw',
          label: title,
          children: <JsonBlock value={value || {}} />,
        },
      ]}
    />
  );
}

export function StatusTag({ status, children }: StatusTagProps) {
  const tone = toneForStatus(status);
  const label = children ?? (typeof status === 'boolean' ? (status ? '启用' : '停用') : (status || '未知'));
  return <Tag color={colorForTone(tone)}>{label}</Tag>;
}
