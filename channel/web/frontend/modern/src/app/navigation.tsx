import {
  ApiOutlined,
  ApartmentOutlined,
  AppstoreOutlined,
  BarChartOutlined,
  BuildOutlined,
  ClusterOutlined,
  FileTextOutlined,
  MessageOutlined,
  ScheduleOutlined,
  SettingOutlined,
  TeamOutlined,
} from '@ant-design/icons';
import type { MenuProps } from 'antd';
import type { ReactNode } from 'react';

export interface ConsoleNavItem {
  key: string;
  icon: ReactNode;
  label: string;
}

export const tenantNavItems: ConsoleNavItem[] = [
  { key: '/chat', icon: <MessageOutlined />, label: '对话' },
  { key: '/agents', icon: <AppstoreOutlined />, label: 'AI 员工' },
  { key: '/tenant-models', icon: <SettingOutlined />, label: '租户模型' },
  { key: '/skills', icon: <BuildOutlined />, label: '技能' },
  { key: '/mcp', icon: <ApiOutlined />, label: 'MCP 连接' },
  { key: '/channels', icon: <ClusterOutlined />, label: '渠道接入' },
  { key: '/usage', icon: <BarChartOutlined />, label: '用量分析' },
  { key: '/tasks', icon: <ScheduleOutlined />, label: '任务调度' },
  { key: '/tenant-users', icon: <TeamOutlined />, label: '租户成员' },
];

export const platformNavItems: ConsoleNavItem[] = [
  { key: '/platform/models', icon: <SettingOutlined />, label: '平台模型' },
  { key: '/platform/tenants', icon: <ApartmentOutlined />, label: '租户管理' },
  { key: '/platform/logs', icon: <FileTextOutlined />, label: '运行日志' },
];

export function getFlatMenuItemsForRole(isPlatformAdmin: boolean): ConsoleNavItem[] {
  return isPlatformAdmin ? platformNavItems : tenantNavItems;
}

function toMenuItems(items: ConsoleNavItem[]): NonNullable<MenuProps['items']> {
  return items.map((item) => ({
    key: item.key,
    icon: item.icon,
    label: item.label,
  }));
}

export function getMenuItemsForRole(isPlatformAdmin: boolean): MenuProps['items'] {
  if (isPlatformAdmin) {
    return [
      {
        type: 'group',
        label: '平台管理',
        children: toMenuItems(platformNavItems),
      },
    ];
  }

  return [
    {
      type: 'group',
      label: '工作台',
      children: toMenuItems(tenantNavItems.filter((item) => item.key === '/chat')),
    },
    {
      type: 'group',
      label: '数字员工',
      children: toMenuItems(tenantNavItems.filter((item) => item.key === '/agents')),
    },
    {
      type: 'group',
      label: '模型与能力',
      children: toMenuItems(tenantNavItems.filter((item) => ['/tenant-models', '/skills', '/mcp'].includes(item.key))),
    },
    {
      type: 'group',
      label: '渠道接入',
      children: toMenuItems(tenantNavItems.filter((item) => item.key === '/channels')),
    },
    {
      type: 'group',
      label: '运营观测',
      children: toMenuItems(tenantNavItems.filter((item) => ['/usage', '/tasks'].includes(item.key))),
    },
    {
      type: 'group',
      label: '组织成员',
      children: toMenuItems(tenantNavItems.filter((item) => item.key === '/tenant-users')),
    },
  ];
}
