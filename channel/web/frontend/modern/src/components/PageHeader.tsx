import { Typography } from 'antd';
import type { ReactNode } from 'react';

interface PageHeaderProps {
  title: ReactNode;
  description?: ReactNode;
  meta?: ReactNode;
  extra?: ReactNode;
  className?: string;
  titleLevel?: 1 | 2 | 3 | 4 | 5;
}

export function PageHeader({
  title,
  description,
  meta,
  extra,
  className,
  titleLevel = 3,
}: PageHeaderProps) {
  return (
    <header className={['page-header', className].filter(Boolean).join(' ')}>
      <div className="page-header-heading">
        <Typography.Title level={titleLevel} className="page-header-title">
          {title}
        </Typography.Title>
        {description ? <Typography.Text className="page-header-description">{description}</Typography.Text> : null}
        {meta ? <div className="page-header-meta">{meta}</div> : null}
      </div>
      {extra ? <div className="page-header-extra">{extra}</div> : null}
    </header>
  );
}
