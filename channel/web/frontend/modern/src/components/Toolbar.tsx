import { Space } from 'antd';
import type { ReactNode } from 'react';

interface ToolbarProps {
  start?: ReactNode;
  end?: ReactNode;
  children?: ReactNode;
  align?: 'start' | 'end';
  className?: string;
  ariaLabel?: string;
}

export function Toolbar({
  start,
  end,
  children,
  align = 'end',
  className,
  ariaLabel = '页面工具栏',
}: ToolbarProps) {
  if (start || end) {
    return (
      <div className={['page-toolbar page-toolbar-split', className].filter(Boolean).join(' ')} role="group" aria-label={ariaLabel}>
        {start ? (
          <div className="page-toolbar-slot page-toolbar-slot-start">
            <Space wrap size={0}>
              {start}
            </Space>
          </div>
        ) : null}
        {end ? (
          <div className="page-toolbar-slot page-toolbar-slot-end">
            <Space wrap size={0}>
              {end}
            </Space>
          </div>
        ) : null}
      </div>
    );
  }

  return (
    <div className={['page-toolbar', `page-toolbar-${align}`, className].filter(Boolean).join(' ')} role="group" aria-label={ariaLabel}>
      <Space wrap size={0}>
        {children}
      </Space>
    </div>
  );
}
