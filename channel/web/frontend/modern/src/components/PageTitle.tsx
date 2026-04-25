import { Typography } from 'antd';

interface PageTitleProps {
  title: string;
  description?: string;
  extra?: React.ReactNode;
}

export function PageTitle({ title, description, extra }: PageTitleProps) {
  return (
    <div className="console-page-header page-title-compat">
      <div className="console-page-heading">
        <Typography.Title level={4} className="console-page-title">{title}</Typography.Title>
        {description ? <Typography.Text className="console-page-description">{description}</Typography.Text> : null}
      </div>
      {extra}
    </div>
  );
}
