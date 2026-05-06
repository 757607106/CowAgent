import { AgentItem } from '../types';

export const AGENT_AVATAR_OPTIONS = [
  {
    key: 'chibi-service-rep',
    label: '形象 01',
    src: new URL('../../../avatars/chibi-service-rep.png', import.meta.url).href,
  },
  {
    key: 'flat-data-analyst',
    label: '形象 02',
    src: new URL('../../../avatars/flat-data-analyst.png', import.meta.url).href,
  },
  {
    key: 'chibi-sales-expert',
    label: '形象 03',
    src: new URL('../../../avatars/chibi-sales-expert.png', import.meta.url).href,
  },
  {
    key: 'flat-ops-engineer',
    label: '形象 04',
    src: new URL('../../../avatars/flat-ops-engineer.png', import.meta.url).href,
  },
  {
    key: 'chibi-researcher',
    label: '形象 05',
    src: new URL('../../../avatars/chibi-researcher.png', import.meta.url).href,
  },
  {
    key: 'flat-content-writer',
    label: '形象 06',
    src: new URL('../../../avatars/flat-content-writer.png', import.meta.url).href,
  },
  {
    key: 'flat-security',
    label: '形象 07',
    src: new URL('../../../avatars/flat-security.png', import.meta.url).href,
  },
  {
    key: 'chibi-inspector',
    label: '形象 08',
    src: new URL('../../../avatars/chibi-inspector.png', import.meta.url).href,
  },
  {
    key: 'flat-tech-support',
    label: '形象 09',
    src: new URL('../../../avatars/flat-tech-support.png', import.meta.url).href,
  },
  {
    key: 'flat-hr-people',
    label: '形象 10',
    src: new URL('../../../avatars/flat-hr-people.png', import.meta.url).href,
  },
  {
    key: 'chibi-detective',
    label: '形象 11',
    src: new URL('../../../avatars/chibi-detective.png', import.meta.url).href,
  },
  {
    key: 'chibi-release-mgr',
    label: '形象 12',
    src: new URL('../../../avatars/chibi-release-mgr.png', import.meta.url).href,
  },
  {
    key: 'chibi-consultant',
    label: '形象 13',
    src: new URL('../../../avatars/chibi-consultant.png', import.meta.url).href,
  },
  {
    key: 'chibi-ops-engineer',
    label: '形象 14',
    src: new URL('../../../avatars/chibi-ops-engineer.png', import.meta.url).href,
  },
  {
    key: 'flat-service-rep',
    label: '形象 15',
    src: new URL('../../../avatars/flat-service-rep.png', import.meta.url).href,
  },
  {
    key: 'flat-sales-manager',
    label: '形象 16',
    src: new URL('../../../avatars/flat-sales-manager.png', import.meta.url).href,
  },
] as const;

export const DEFAULT_AGENT_AVATAR_KEY = AGENT_AVATAR_OPTIONS[0].key;
export const AGENT_AVATAR_KEYS = new Set<string>(AGENT_AVATAR_OPTIONS.map((option) => option.key));

export type AgentAvatarOption = (typeof AGENT_AVATAR_OPTIONS)[number];

export function avatarOptionByKey(value: unknown): AgentAvatarOption {
  const key = typeof value === 'string' && AGENT_AVATAR_KEYS.has(value) ? value : DEFAULT_AGENT_AVATAR_KEY;
  return AGENT_AVATAR_OPTIONS.find((option) => option.key === key) || AGENT_AVATAR_OPTIONS[0];
}

export function agentAvatarOption(agent: AgentItem | null | undefined): AgentAvatarOption {
  const metadata = agent?.metadata || {};
  return avatarOptionByKey(metadata.avatar_key || metadata.avatar);
}
