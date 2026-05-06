import { Typography } from 'antd';

interface PageTitleProps {
  title: string;
  description?: string;
  extra?: React.ReactNode;
}

export function PageTitle({ title, description, extra }: PageTitleProps) {
  return (
    <div className="console-embedded-header">
      <div className="console-embedded-heading">
        <Typography.Title level={4} className="console-embedded-title">{title}</Typography.Title>
        {description ? <Typography.Text className="console-embedded-description">{description}</Typography.Text> : null}
      </div>
      {extra ? <div className="console-embedded-actions">{extra}</div> : null}
    </div>
  );
}
