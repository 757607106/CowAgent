import { Tabs } from 'antd';
import { useEffect, useState } from 'react';
import { ConsolePage } from '../components/console';
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
    <ConsolePage
      className="channel-access-page"
        title="渠道接入"
      >
      <div className="channel-access-shell">
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
      </div>
    </ConsolePage>
  );
}
