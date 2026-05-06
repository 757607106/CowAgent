import { MessageOutlined } from '@ant-design/icons';
import type { ConversationItemType } from '@ant-design/x';
import { DEFAULT_AGENT_ID, DEFAULT_AGENT_NAME } from '../context/runtime';
import type { RuntimeScope, SessionItem } from '../types';

const SESSION_KEY_PREFIX = 'cowagent-web-session-id';

export const HISTORY_PAGE_SIZE = 200;

export function createSessionId(): string {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return `session_${crypto.randomUUID()}`;
  }
  return `session_${Date.now()}_${Math.random().toString(16).slice(2, 10)}`;
}

function getScopeStorageSegment(scope: RuntimeScope): string {
  const tenantSegment = `tenant:${scope.tenantId || 'default'}`;
  if (scope.bindingId) return `${tenantSegment}:binding:${scope.bindingId}`;
  if (scope.agentId) return `${tenantSegment}:agent:${scope.agentId}`;
  return `${tenantSegment}:default`;
}

function getScopeStorageKey(scope: RuntimeScope): string {
  return `${SESSION_KEY_PREFIX}:${getScopeStorageSegment(scope)}`;
}

export function readStoredSessionId(scope: RuntimeScope): string {
  if (typeof window === 'undefined') return '';
  return localStorage.getItem(getScopeStorageKey(scope)) || '';
}

export function persistSessionId(scope: RuntimeScope, sessionId: string) {
  if (typeof window === 'undefined') return;
  localStorage.setItem(getScopeStorageKey(scope), sessionId);
}

export function buildConversationKey(scope: RuntimeScope, sessionId: string): string {
  return `${getScopeStorageSegment(scope)}:${sessionId}`;
}

export function getScopeLabel(scope: RuntimeScope): string {
  if (scope.bindingId) return `绑定 ${scope.bindingId}`;
  if (scope.agentId === DEFAULT_AGENT_ID) return DEFAULT_AGENT_NAME;
  if (scope.agentId) return `AI 员工 ${scope.agentId}`;
  return DEFAULT_AGENT_NAME;
}

function getSessionTimestamp(session: SessionItem): number {
  const raw = session.last_active || session.updated_at || session.created_at || Date.now() / 1000;
  const numeric = Number(raw);
  return Number.isFinite(numeric) ? numeric : Date.now() / 1000;
}

function getSessionGroupLabel(timestampSeconds: number): string {
  const target = new Date(timestampSeconds * 1000);
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const yesterday = new Date(today);
  yesterday.setDate(today.getDate() - 1);

  if (target >= today) return '今天';
  if (target >= yesterday) return '昨天';
  return '更早';
}

function formatSessionMeta(timestampSeconds: number, msgCount?: number): string {
  const text = new Intl.DateTimeFormat('zh-CN', {
    month: 'numeric',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(timestampSeconds * 1000));

  if (typeof msgCount === 'number' && msgCount > 0) {
    return `${text} · ${msgCount} 条消息`;
  }
  return text;
}

export function buildConversationItems(
  sessions: SessionItem[],
  currentSessionId: string,
  currentMessageCount: number,
): ConversationItemType[] {
  const sessionMap = new Map<string, SessionItem>();
  sessions.forEach((session) => sessionMap.set(session.session_id, session));

  if (currentSessionId && !sessionMap.has(currentSessionId)) {
    const now = Math.floor(Date.now() / 1000);
    sessionMap.set(currentSessionId, {
      session_id: currentSessionId,
      title: '新对话',
      created_at: now,
      last_active: now,
      msg_count: currentMessageCount,
    });
  }

  return Array.from(sessionMap.values())
    .sort((left, right) => getSessionTimestamp(right) - getSessionTimestamp(left))
    .map((session) => {
      const timestamp = getSessionTimestamp(session);
      const title = session.title || '新对话';
      return {
        key: session.session_id,
        group: getSessionGroupLabel(timestamp),
        label: (
          <div className="chat-session-label">
            <span className="chat-session-label-title">{title}</span>
            <span className="chat-session-label-meta">{formatSessionMeta(timestamp, session.msg_count)}</span>
          </div>
        ),
        icon: <MessageOutlined />,
      } satisfies ConversationItemType;
    });
}
