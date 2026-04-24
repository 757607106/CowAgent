import { Card, Tabs } from 'antd';
import { useEffect, useState } from 'react';
import { PageTitle } from '../components/PageTitle';
import BindingsPage from './BindingsPage';
import ChannelsPage from './ChannelsPage';

interface ChannelAccessPageProps {
  defaultTab?: 'bindings' | 'channels';
}

export default function ChannelAccessPage({ defaultTab = 'bindings' }: ChannelAccessPageProps) {
  const [activeKey, setActiveKey] = useState(defaultTab);

  useEffect(() => {
    setActiveKey(defaultTab);
  }, [defaultTab]);

  return (
    <div className="channel-access-page">
      <PageTitle
        title="渠道接入"
        description="数字员工通过绑定接入不同渠道，并在微信、飞书等入口中执行工作。"
      />
      <Card className="channel-access-shell">
        <Tabs
          activeKey={activeKey}
          onChange={(key) => setActiveKey(key as 'bindings' | 'channels')}
          items={[
            {
              key: 'bindings',
              label: '绑定',
              children: <BindingsPage embedded />,
            },
            {
              key: 'channels',
              label: '渠道',
              children: <ChannelsPage embedded />,
            },
          ]}
        />
      </Card>
    </div>
  );
}
