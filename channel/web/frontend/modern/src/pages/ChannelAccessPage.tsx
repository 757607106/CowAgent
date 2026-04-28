import { Tabs } from 'antd';
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ConsolePage } from '../components/console';
import BindingsPage from './BindingsPage';
import ChannelsPage from './ChannelsPage';

interface ChannelAccessPageProps {
  defaultTab?: 'bindings' | 'channels';
}

export default function ChannelAccessPage({ defaultTab = 'bindings' }: ChannelAccessPageProps) {
  const [activeKey, setActiveKey] = useState(defaultTab);
  const navigate = useNavigate();

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
          onChange={(key) => {
            const nextKey = key as 'bindings' | 'channels';
            setActiveKey(nextKey);
            navigate(nextKey === 'bindings' ? '/bindings' : '/channels');
          }}
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
