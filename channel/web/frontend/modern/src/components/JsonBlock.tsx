import { Typography } from 'antd';
import type { CSSProperties } from 'react';

interface JsonBlockProps {
  value: unknown;
  style?: CSSProperties;
}

export function JsonBlock({ value, style }: JsonBlockProps) {
  const content = typeof value === 'string' ? value : JSON.stringify(value, null, 2);
  return (
    <Typography.Paragraph
      style={{
        margin: 0,
        whiteSpace: 'pre-wrap',
        fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace',
        fontSize: 12,
        lineHeight: 1.45,
        background: '#fafafa',
        border: '1px solid #f0f0f0',
        borderRadius: 8,
        padding: 12,
        maxHeight: 360,
        overflow: 'auto',
        ...style,
      }}
    >
      {content}
    </Typography.Paragraph>
  );
}
