import { Card, Collapse, Space, Table, Tag, Typography, type TableProps } from 'antd';
import type { ReactNode } from 'react';
import { JsonBlock } from './JsonBlock';

type Tone = 'default' | 'success' | 'processing' | 'warning' | 'error' | 'disabled';

interface ConsolePageProps {
  title: string;
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
    <section className={['console-page', className].filter(Boolean).join(' ')}>
      <header className="console-page-header">
        <div className="console-page-heading">
          <Typography.Title level={3} className="console-page-title">
            {title}
          </Typography.Title>
          {description ? <Typography.Text className="console-page-description">{description}</Typography.Text> : null}
        </div>
        {actions ? <div className="console-page-actions">{actions}</div> : null}
      </header>
      {children}
    </section>
  );
}

export function PageToolbar({ children, align = 'end' }: PageToolbarProps) {
  return (
    <div className={`page-toolbar page-toolbar-${align}`}>
      <Space wrap size={8}>
        {children}
      </Space>
    </div>
  );
}

function fallbackRowKey<T extends object>(record: T, index?: number) {
  const source = record as Record<string, unknown>;
  const key = source.id ?? source.key ?? source.agent_id ?? source.tenant_id ?? source.user_id ?? source.name ?? index;
  return typeof key === 'string' || typeof key === 'number' ? key : String(index ?? 0);
}

export function DataTableShell<T extends object>({ title, toolbar, compact, className, rowKey, ...tableProps }: DataTableShellProps<T>) {
  return (
    <Card className={['data-table-shell', compact ? 'data-table-shell-compact' : '', className].filter(Boolean).join(' ')}>
      {title || toolbar ? (
        <div className="data-table-shell-head">
          <div className="data-table-shell-title">{title}</div>
          {toolbar}
        </div>
      ) : null}
      <Table<T> rowKey={rowKey ?? fallbackRowKey} size={compact ? 'small' : undefined} {...tableProps} />
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
