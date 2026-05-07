import { Avatar, Badge, Tag, Tooltip, Typography } from 'antd';
import type { ReactNode } from 'react';
import { EntityActionBar } from './console';

type EmployeeStatus = 'success' | 'processing' | 'default' | 'warning' | 'error';

interface EmployeeMetric {
  key: string;
  label: string;
  value: ReactNode;
  icon?: ReactNode;
  tooltip?: ReactNode;
}

interface EmployeeAction {
  key: string;
  label: string;
  icon?: ReactNode;
  tooltip?: ReactNode;
  danger?: boolean;
  disabled?: boolean;
  confirmTitle?: ReactNode;
  onClick?: () => void;
}

interface EmployeeCardProps {
  name: string;
  id: string;
  position?: string;
  avatarSrc?: string;
  initial: string;
  status: EmployeeStatus;
  statusLabel: string;
  model?: string;
  tags?: ReactNode[];
  metrics: EmployeeMetric[];
  actions: EmployeeAction[];
}

export function EmployeeCard({
  name,
  id,
  position,
  avatarSrc,
  initial,
  status,
  statusLabel,
  model,
  tags = [],
  metrics,
  actions,
}: EmployeeCardProps) {
  return (
    <article className={`employee-card employee-card-${status}`}>
      <header className="employee-card-head">
        <div className="employee-identity">
          <span className="employee-avatar-ring">
            <Avatar src={avatarSrc} className="employee-avatar">{initial}</Avatar>
          </span>
          <div className="employee-title-wrap">
            <Typography.Title level={5} className="employee-name" title={name}>
              {name}
            </Typography.Title>
            <Typography.Text className="employee-position" title={position || id}>
              {position || id}
            </Typography.Text>
          </div>
        </div>
        <Badge status={status} text={statusLabel} className="employee-status" />
      </header>

      <div className="employee-card-body">
        <div className="employee-model-row">
          {model ? <Tag color="blue">{model}</Tag> : <Tag>模型待配置</Tag>}
          {tags.map((tag, index) => (
            <span key={index} className="employee-extra-tag">{tag}</span>
          ))}
        </div>
        <div className="employee-metrics">
          {metrics.map((metric) => {
            const content = (
              <span className="employee-metric">
                {metric.icon ? <span className="employee-metric-icon">{metric.icon}</span> : null}
                <strong>{metric.value}</strong>
                <span>{metric.label}</span>
              </span>
            );
            return metric.tooltip ? (
              <Tooltip key={metric.key} title={metric.tooltip}>{content}</Tooltip>
            ) : (
              <span key={metric.key}>{content}</span>
            );
          })}
        </div>
      </div>

      <footer className="employee-card-actions">
        <EntityActionBar actions={actions} />
      </footer>
    </article>
  );
}
