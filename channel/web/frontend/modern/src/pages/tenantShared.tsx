import { AdvancedJsonPanel, StatusTag } from '../components/console';
import type { TenantItem } from '../types';

export const TENANT_STATUS_OPTIONS = [
  { label: 'active', value: 'active' },
  { label: 'disabled', value: 'disabled' },
  { label: 'deleted', value: 'deleted' },
];

export function renderTenantTitle(value: string, row: TenantItem) {
  return (
    <span className="entity-title-cell">
      <span className="entity-title-cell-main">{value}</span>
      <span className="entity-title-cell-meta">{row.tenant_id}</span>
    </span>
  );
}

export function renderTenantStatus(value: string) {
  return <StatusTag status={value}>{value}</StatusTag>;
}

export function renderTenantMetadata(row: TenantItem) {
  return <AdvancedJsonPanel title="租户扩展信息" value={row.metadata || {}} />;
}
