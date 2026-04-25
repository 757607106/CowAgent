import { Space, Typography } from 'antd';

interface PageTitleProps {
  title: string;
  description?: string;
  extra?: React.ReactNode;
}

export function PageTitle({ title, description, extra }: PageTitleProps) {
  return (
    <Space style={{ width: '100%', justifyContent: 'space-between', marginBottom: 16 }} align="start">
      <div>
        <Typography.Title level={4} style={{ margin: 0 }}>{title}</Typography.Title>
        {description ? <Typography.Text type="secondary">{description}</Typography.Text> : null}
      </div>
      {extra}
    </Space>
  );
}
