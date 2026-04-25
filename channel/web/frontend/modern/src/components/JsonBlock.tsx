import { Typography } from 'antd';
import type { CSSProperties } from 'react';

interface JsonBlockProps {
  value: unknown;
  className?: string;
  style?: CSSProperties;
}

export function JsonBlock({ value, className, style }: JsonBlockProps) {
  const content = typeof value === 'string' ? value : JSON.stringify(value, null, 2);
  return (
    <Typography.Paragraph
      className={['json-block', className].filter(Boolean).join(' ')}
      style={style}
    >
      {content}
    </Typography.Paragraph>
  );
}
