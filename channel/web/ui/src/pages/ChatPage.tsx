import {
  Attachments,
  Bubble,
  Conversations,
  Prompts,
  Sender,
  Welcome,
  type BubbleItemType,
  type ConversationItemType,
} from '@ant-design/x';
import {
  BulbOutlined,
  CheckOutlined,
  CompassOutlined,
  CopyOutlined,
  DeleteOutlined,
  DeploymentUnitOutlined,
  LoadingOutlined,
  MessageOutlined,
  PaperClipOutlined,
  PlusOutlined,
  ReloadOutlined,
  RobotOutlined,
  StopOutlined,
  UnorderedListOutlined,
  UserOutlined,
} from '@ant-design/icons';
import { App, Avatar, Button, Empty, Popconfirm, Space, Spin, Tag, Tooltip, Typography } from 'antd';
import { useCallback, useEffect, useMemo, useRef, useState, type ComponentRef, type KeyboardEvent as ReactKeyboardEvent } from 'react';
import {
  type CowAgentChatMessage,
  type CowAgentChatRequest,
  createAssistantErrorMessage,
  createAssistantPlaceholderMessage,
  createContextDividerMessage,
  createCowAgentChatProvider,
  extractAssistantReply,
  parseHistoryMessages,
} from '../chat/CowAgentChatProvider';
import { AssistantMessageFlow } from '../chat/AssistantMessageFlow';
import { MarkdownBlock } from '../chat/ChatMarkdown';
import { useRuntimeScope } from '../context/runtime';
import { asAttachment, api } from '../services/api';
import { scopeBody } from '../services/http';
import type { ChatAttachment, RuntimeScope, SessionItem } from '../types';
import { useXChat, type SSEOutput } from '@ant-design/x-sdk';

const SESSION_KEY_PREFIX = 'cowagent-web-session-id';
const HISTORY_PAGE_SIZE = 200;
const SLASH_COMMANDS = [
  { cmd: '/help', desc: '显示命令帮助' },
  { cmd: '/status', desc: '查看运行状态' },
  { cmd: '/context', desc: '查看对话上下文' },
  { cmd: '/context clear', desc: '清除对话上下文' },
  { cmd: '/skill list', desc: '查看已安装技能' },
  { cmd: '/skill list --remote', desc: '浏览技能广场' },
  { cmd: '/skill search ', desc: '搜索技能' },
  { cmd: '/skill install ', desc: '安装技能' },
  { cmd: '/skill uninstall ', desc: '卸载技能' },
  { cmd: '/skill info ', desc: '查看技能详情' },
  { cmd: '/skill enable ', desc: '启用技能' },
  { cmd: '/skill disable ', desc: '禁用技能' },
  { cmd: '/memory dream ', desc: '手动触发记忆蒸馏' },
  { cmd: '/knowledge', desc: '查看知识库统计' },
  { cmd: '/knowledge list', desc: '查看知识库文件树' },
  { cmd: '/knowledge on', desc: '开启知识库' },
  { cmd: '/knowledge off', desc: '关闭知识库' },
  { cmd: '/config', desc: '查看当前配置' },
  { cmd: '/logs', desc: '查看最近日志' },
  { cmd: '/version', desc: '查看版本' },
] as const;

function createSessionId(): string {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return `session_${crypto.randomUUID()}`;
  }
  return `session_${Date.now()}_${Math.random().toString(16).slice(2, 10)}`;
}

function getScopeStorageSegment(scope: RuntimeScope): string {
  if (scope.bindingId) return `binding:${scope.bindingId}`;
  if (scope.agentId) return `agent:${scope.agentId}`;
  return 'workspace';
}

function getScopeStorageKey(scope: RuntimeScope): string {
  return `${SESSION_KEY_PREFIX}:${getScopeStorageSegment(scope)}`;
}

function readStoredSessionId(scope: RuntimeScope): string {
  if (typeof window === 'undefined') return '';
  return localStorage.getItem(getScopeStorageKey(scope)) || '';
}

function persistSessionId(scope: RuntimeScope, sessionId: string) {
  if (typeof window === 'undefined') return;
  localStorage.setItem(getScopeStorageKey(scope), sessionId);
}

function buildConversationKey(scope: RuntimeScope, sessionId: string): string {
  return `${getScopeStorageSegment(scope)}:${sessionId}`;
}

function getScopeLabel(scope: RuntimeScope): string {
  if (scope.bindingId) return `绑定 ${scope.bindingId}`;
  if (scope.agentId) return `智能体 ${scope.agentId}`;
  return '默认助手（当前工作区）';
}

function formatClock(value: number): string {
  return new Intl.DateTimeFormat('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
  }).format(value);
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

function asText(value: unknown): string {
  if (value === undefined || value === null) return '';
  if (typeof value === 'string') return value;
  if (typeof value === 'number' || typeof value === 'boolean') return String(value);
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

function renderUserAttachment(attachment: ChatAttachment) {
  if (attachment.file_type === 'image' && attachment.preview_url) {
    return (
      <img
        key={attachment.file_path}
        src={attachment.preview_url}
        alt={attachment.file_name}
        className="chat-user-attachment-image"
      />
    );
  }

  return (
    <span key={attachment.file_path} className="chat-user-attachment-chip">
      <PaperClipOutlined />
      {attachment.file_name}
    </span>
  );
}

function FooterCopyButton({ text }: { text?: string }) {
  const [copied, setCopied] = useState(false);
  const value = (text || '').trim();

  if (!value) return null;

  return (
    <button
      type="button"
      className="chat-bubble-copy-btn"
      title={copied ? '已复制' : '复制回复'}
      onClick={async () => {
        try {
          await navigator.clipboard.writeText(value);
          setCopied(true);
          window.setTimeout(() => setCopied(false), 1200);
        } catch {
          setCopied(false);
        }
      }}
    >
      {copied ? <CheckOutlined /> : <CopyOutlined />}
    </button>
  );
}

function buildBubbleItems(
  messages: ReturnType<typeof useXChat<CowAgentChatMessage, CowAgentChatMessage, CowAgentChatRequest, SSEOutput>>['messages'],
  scopeLabel: string,
): BubbleItemType[] {
  return messages.map((item) => {
    const assistantText = item.message.role === 'assistant' ? item.message.content?.text || '' : '';

    return {
      key: item.id,
      role: item.message.role === 'assistant' ? 'assistant' : item.message.role === 'divider' ? 'system' : item.message.role,
      content: item.message,
      status: item.status,
      extraInfo: {
        createdAt: item.message.createdAt,
        scopeLabel,
        copyText: assistantText,
        canCopy: item.message.role === 'assistant' && item.status === 'success' && Boolean(assistantText.trim()),
      },
    };
  });
}

function buildConversationItems(
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

const promptItems = [
  {
    key: 'capability',
    label: '介绍你当前可用的能力',
    description: '快速确认当前智能体的角色、工具和边界',
    icon: <CompassOutlined />,
  },
  {
    key: 'workspace',
    label: '梳理一下这个项目的核心模块',
    description: '结合当前工作区给出目录和职责划分',
    icon: <DeploymentUnitOutlined />,
  },
  {
    key: 'toolchain',
    label: '列出当前工作区可用的工具链',
    description: '看看现在能调用哪些工具、技能和平台能力',
    icon: <UnorderedListOutlined />,
  },
];

export default function ChatPage() {
  const app = App.useApp();
  const { scope } = useRuntimeScope();
  const provider = useMemo(() => createCowAgentChatProvider(), []);
  const attachmentsRef = useRef<ComponentRef<typeof Attachments>>(null);
  const pendingTitleRef = useRef<{
    conversationKey: string;
    sessionId: string;
    userMessage: string;
  } | null>(null);
  const previousRequestingRef = useRef(false);

  const [sessionId, setSessionId] = useState<string>(() => readStoredSessionId(scope));
  const [sessions, setSessions] = useState<SessionItem[]>([]);
  const [sessionsLoading, setSessionsLoading] = useState(false);
  const [attachments, setAttachments] = useState<ChatAttachment[]>([]);
  const [attachmentPanelOpen, setAttachmentPanelOpen] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [historyHasMore, setHistoryHasMore] = useState(false);
  const [draft, setDraft] = useState('');
  const [dragOver, setDragOver] = useState(false);
  const [slashActiveIdx, setSlashActiveIdx] = useState(0);
  const [slashHidden, setSlashHidden] = useState(false);
  const inputHistoryRef = useRef<string[]>([]);
  const historyIndexRef = useRef(-1);
  const historyDraftRef = useRef('');

  const scopeLabel = useMemo(() => getScopeLabel(scope), [scope.agentId, scope.bindingId]);
  const conversationKey = useMemo(
    () => buildConversationKey(scope, sessionId || 'draft'),
    [scope.agentId, scope.bindingId, sessionId],
  );

  const loadSessions = useCallback(async (resetActive = false) => {
    setSessionsLoading(true);
    try {
      const data = await api.listSessions(scope, 1, 200);
      const nextSessions = data.sessions || [];
      setSessions(nextSessions);

      if (resetActive) {
        const stored = readStoredSessionId(scope);
        const nextActive = stored || nextSessions[0]?.session_id || createSessionId();
        persistSessionId(scope, nextActive);
        setSessionId(nextActive);
      }
    } catch (error) {
      app.message.error(error instanceof Error ? error.message : '加载会话失败');
    } finally {
      setSessionsLoading(false);
    }
  }, [app.message, scope.agentId, scope.bindingId]);

  useEffect(() => {
    setAttachments([]);
    setAttachmentPanelOpen(false);
    void loadSessions(true);
  }, [loadSessions]);

  const defaultMessages = useCallback(async () => {
    if (!sessionId) {
      setHistoryHasMore(false);
      return [];
    }

    const data = await api.history(scope, sessionId, 1, HISTORY_PAGE_SIZE);
    setHistoryHasMore(Boolean(data.has_more));
    return parseHistoryMessages(data.messages || [], data.context_start_seq || 0);
  }, [scope.agentId, scope.bindingId, sessionId]);

  const {
    messages,
    setMessages,
    onRequest,
    abort,
    isRequesting,
    isDefaultMessagesRequesting,
  } = useXChat<CowAgentChatMessage, CowAgentChatMessage, CowAgentChatRequest, SSEOutput>({
    provider,
    conversationKey,
    defaultMessages,
    parser: (message) => message,
    requestPlaceholder: createAssistantPlaceholderMessage(),
    requestFallback: (_, info) => createAssistantErrorMessage(info.messageInfo?.message, info.error),
  });

  const conversationItems = useMemo(
    () => buildConversationItems(sessions, sessionId, messages.length),
    [sessions, sessionId, messages.length],
  );
  const bubbleItems = useMemo(() => buildBubbleItems(messages, scopeLabel), [messages, scopeLabel]);
  const hasPersistedSession = useMemo(
    () => sessions.some((session) => session.session_id === sessionId),
    [sessions, sessionId],
  );
  const activeSession = useMemo(
    () => sessions.find((session) => session.session_id === sessionId),
    [sessions, sessionId],
  );
  const attachmentItems = useMemo(() => attachments.map((attachment) => ({
    uid: attachment.file_path,
    name: attachment.file_name,
    status: 'done' as const,
    url: attachment.preview_url || attachment.file_path,
    thumbUrl: attachment.file_type === 'image' ? (attachment.preview_url || attachment.file_path) : undefined,
    description: attachment.file_type === 'image'
      ? '图片附件'
      : attachment.file_type === 'video'
        ? '视频附件'
      : '文件附件',
  })), [attachments]);
  const slashFiltered = useMemo(() => {
    const query = draft.trimStart();
    if (!query.startsWith('/')) return [];
    return SLASH_COMMANDS.filter((item) => item.cmd.toLowerCase().startsWith(query.toLowerCase()));
  }, [draft]);
  const slashMenuVisible = slashFiltered.length > 0 && !slashHidden;

  const refreshConversation = useCallback(async () => {
    if (!sessionId) return;
    try {
      const data = await api.history(scope, sessionId, 1, HISTORY_PAGE_SIZE);
      setHistoryHasMore(Boolean(data.has_more));
      setMessages(parseHistoryMessages(data.messages || [], data.context_start_seq || 0));
    } catch (error) {
      app.message.error(error instanceof Error ? error.message : '刷新历史失败');
    }
  }, [app.message, scope.agentId, scope.bindingId, sessionId, setMessages]);

  const activateSession = useCallback((nextSessionId: string) => {
    persistSessionId(scope, nextSessionId);
    setSessionId(nextSessionId);
    setAttachments([]);
    setAttachmentPanelOpen(false);
  }, [scope.agentId, scope.bindingId]);

  const newChat = useCallback(() => {
    if (isRequesting) abort();
    pendingTitleRef.current = null;
    const nextSessionId = createSessionId();
    const now = Math.floor(Date.now() / 1000);
    persistSessionId(scope, nextSessionId);
    setSessionId(nextSessionId);
    setAttachments([]);
    setAttachmentPanelOpen(false);
    setHistoryHasMore(false);
    setSessions((prev) => [{
      session_id: nextSessionId,
      title: '新对话',
      created_at: now,
      last_active: now,
      msg_count: 0,
    }, ...prev.filter((item) => item.session_id !== nextSessionId)]);
  }, [abort, isRequesting, scope.agentId, scope.bindingId]);

  const removeSession = useCallback(async (targetSessionId: string) => {
    try {
      await api.deleteSession(scope, targetSessionId);
      app.message.success('会话已删除');
      setSessions((prev) => prev.filter((item) => item.session_id !== targetSessionId));

      if (targetSessionId === sessionId) {
        newChat();
      } else {
        void loadSessions(false);
      }
    } catch (error) {
      app.message.error(error instanceof Error ? error.message : '删除会话失败');
    }
  }, [app.message, loadSessions, newChat, scope.agentId, scope.bindingId, sessionId]);

  const clearContext = useCallback(async () => {
    if (!sessionId) return;
    try {
      await api.clearContext(scope, sessionId);
      setMessages((prev) => [...prev, createContextDividerMessage()]);
      app.message.success('上下文已清空');
    } catch (error) {
      app.message.error(error instanceof Error ? error.message : '清空上下文失败');
    }
  }, [app.message, scope.agentId, scope.bindingId, sessionId, setMessages]);

  const uploadFiles = useCallback(async (files: File[]) => {
    if (!files.length || !sessionId) return;
    setUploading(true);
    try {
      const uploaded = await Promise.all(
        files.map((file) => api.uploadFile(scope, sessionId, file).then(asAttachment)),
      );
      setAttachments((prev) => [...prev, ...uploaded]);
      setAttachmentPanelOpen(true);
      app.message.success(`已上传 ${uploaded.length} 个附件`);
    } catch (error) {
      app.message.error(error instanceof Error ? error.message : '上传附件失败');
    } finally {
      setUploading(false);
    }
  }, [app.message, scope.agentId, scope.bindingId, sessionId]);

  const openAttachmentPanel = useCallback(() => {
    setAttachmentPanelOpen(true);
    window.setTimeout(() => {
      attachmentsRef.current?.select({ multiple: true });
    }, 0);
  }, []);

  const submitMessage = useCallback((rawText: string) => {
    const text = rawText.trim();
    if (!text && attachments.length === 0) return;
    if (!sessionId) return;

    if (text) {
      const nextHistory = inputHistoryRef.current.filter((item) => item !== text);
      nextHistory.push(text);
      inputHistoryRef.current = nextHistory.slice(-50);
    }
    historyIndexRef.current = -1;
    historyDraftRef.current = '';
    setDraft('');

    const nextAttachments = [...attachments];
    setAttachments([]);
    setAttachmentPanelOpen(false);

    const userSummary = text || (nextAttachments.length > 0
      ? `附件：${nextAttachments.map((item) => item.file_name).join('、')}`
      : '新消息');

    pendingTitleRef.current = {
      conversationKey,
      sessionId,
      userMessage: userSummary,
    };

    if (!sessions.some((item) => item.session_id === sessionId)) {
      const now = Math.floor(Date.now() / 1000);
      setSessions((prev) => [{
        session_id: sessionId,
        title: '新对话',
        created_at: now,
        last_active: now,
        msg_count: 0,
      }, ...prev.filter((item) => item.session_id !== sessionId)]);
    }

    onRequest({
      session_id: sessionId,
      message: text,
      attachments: nextAttachments,
      timestamp: new Date().toISOString(),
      ...scopeBody(scope),
    });
  }, [attachments, conversationKey, onRequest, scope.agentId, scope.bindingId, sessionId, sessions]);

  const selectSlashCommand = useCallback((command: string) => {
    setDraft(command);
    setSlashHidden(true);
    setSlashActiveIdx(0);
  }, []);

  const handleSenderKeyDown = useCallback((event: ReactKeyboardEvent) => {
    if ((event.nativeEvent as KeyboardEvent).isComposing) return;

    if (slashMenuVisible) {
      if (event.key === 'ArrowDown') {
        event.preventDefault();
        setSlashActiveIdx((current) => Math.min(current + 1, slashFiltered.length - 1));
        return false;
      }

      if (event.key === 'ArrowUp') {
        event.preventDefault();
        setSlashActiveIdx((current) => Math.max(current - 1, 0));
        return false;
      }

      if ((event.key === 'Enter' || event.key === 'Tab') && !event.shiftKey && !event.ctrlKey && !event.metaKey) {
        event.preventDefault();
        const chosen = slashFiltered[slashActiveIdx];
        if (chosen) selectSlashCommand(chosen.cmd);
        return false;
      }

      if (event.key === 'Escape') {
        event.preventDefault();
        setSlashHidden(true);
        return false;
      }
    }

    if (event.key === 'ArrowUp') {
      if (inputHistoryRef.current.length === 0 || draft.includes('\n') || slashMenuVisible) return;
      if (draft.trim() !== '' && historyIndexRef.current < 0) return;
      event.preventDefault();

      if (historyIndexRef.current < 0) {
        historyDraftRef.current = draft;
        historyIndexRef.current = inputHistoryRef.current.length - 1;
      } else if (historyIndexRef.current > 0) {
        historyIndexRef.current -= 1;
      }

      setDraft(inputHistoryRef.current[historyIndexRef.current] || '');
      return;
    }

    if (event.key === 'ArrowDown') {
      if (historyIndexRef.current < 0 || draft.includes('\n') || slashMenuVisible) return;
      event.preventDefault();

      if (historyIndexRef.current < inputHistoryRef.current.length - 1) {
        historyIndexRef.current += 1;
        setDraft(inputHistoryRef.current[historyIndexRef.current] || '');
      } else {
        historyIndexRef.current = -1;
        setDraft(historyDraftRef.current);
        historyDraftRef.current = '';
      }
    }
  }, [draft, selectSlashCommand, slashActiveIdx, slashFiltered, slashMenuVisible]);

  useEffect(() => {
    if (slashFiltered.length === 0) {
      setSlashActiveIdx(0);
      return;
    }
    setSlashActiveIdx((current) => Math.min(current, slashFiltered.length - 1));
  }, [slashFiltered]);

  useEffect(() => {
    if (previousRequestingRef.current && !isRequesting) {
      void loadSessions(false);
    }
    previousRequestingRef.current = isRequesting;
  }, [isRequesting, loadSessions]);

  useEffect(() => {
    const pending = pendingTitleRef.current;
    if (!pending || pending.conversationKey !== conversationKey || isRequesting) return;

    const lastAssistant = [...messages].reverse().find((item) => item.message.role === 'assistant');
    if (!lastAssistant) return;

    if (lastAssistant.status === 'error' || lastAssistant.status === 'abort') {
      pendingTitleRef.current = null;
      return;
    }

    if (lastAssistant.status !== 'success') return;

    const assistantReply = extractAssistantReply(lastAssistant.message);
    pendingTitleRef.current = null;

    void api.generateSessionTitle(scope, pending.sessionId, pending.userMessage, assistantReply)
      .then(() => loadSessions(false))
      .catch(() => undefined);
  }, [conversationKey, isRequesting, loadSessions, messages, scope.agentId, scope.bindingId]);

  const bubbleRole = useMemo(() => ({
    user: {
      placement: 'end' as const,
      variant: 'shadow' as const,
      shape: 'round' as const,
      avatar: <Avatar icon={<UserOutlined />} style={{ background: '#5b8ff9' }} />,
      footerPlacement: 'outer-end' as const,
      footer: (_content: unknown, info: { extraInfo?: Record<string, unknown> }) => (
        <span className="chat-bubble-time">{formatClock(Number(info.extraInfo?.createdAt || Date.now()))}</span>
      ),
      contentRender: (content: CowAgentChatMessage) => (
        <div className="chat-user-stack">
          {content.attachments?.length ? (
            <div className="chat-user-attachments">
              {content.attachments.map(renderUserAttachment)}
            </div>
          ) : null}
          {content.text ? (
            <MarkdownBlock content={content.text} className="msg-content chat-user-markdown user-bubble" />
          ) : null}
        </div>
      ),
    },
    assistant: {
      placement: 'start' as const,
      variant: 'borderless' as const,
      avatar: <Avatar icon={<RobotOutlined />} style={{ background: '#52c41a' }} />,
      footerPlacement: 'outer-start' as const,
      footer: (_content: unknown, info: { extraInfo?: Record<string, unknown> }) => (
        <div className="chat-bubble-meta">
          <span>{String(info.extraInfo?.scopeLabel || scopeLabel)}</span>
          <span>{formatClock(Number(info.extraInfo?.createdAt || Date.now()))}</span>
          {info.extraInfo?.canCopy ? <FooterCopyButton text={String(info.extraInfo.copyText || '')} /> : null}
        </div>
      ),
      contentRender: (content: CowAgentChatMessage, info: { status?: BubbleItemType['status'] }) => {
        const payload = content.content || {
          text: '',
          steps: [],
          media: [],
          streaming: false,
        };

        return <AssistantMessageFlow content={payload} status={info.status} />;
      },
    },
    system: {
      placement: 'start' as const,
      variant: 'borderless' as const,
      avatar: <Avatar icon={<BulbOutlined />} />,
      contentRender: (content: CowAgentChatMessage) => {
        if (content.role === 'divider') {
          return <div className="chat-divider-chip">{content.text || '上下文已清空'}</div>;
        }
        return <Typography.Text>{content.text || asText(content)}</Typography.Text>;
      },
    },
  }), [scopeLabel]);

  return (
    <div className="chat-page">
      <aside className="chat-session-pane">
        <div className="chat-session-head">
          <div>
            <Typography.Title level={5} style={{ margin: 0 }}>会话</Typography.Title>
          </div>
          <Tooltip title="刷新会话列表">
            <Button
              type="text"
              shape="circle"
              icon={<ReloadOutlined />}
              onClick={() => void loadSessions(false)}
            />
          </Tooltip>
        </div>

        <div className="chat-session-body">
          {sessionsLoading && conversationItems.length === 0 ? (
            <div className="chat-session-loading">
              <Spin />
            </div>
          ) : conversationItems.length > 0 ? (
            <Conversations
              items={conversationItems}
              activeKey={sessionId}
              groupable={{
                label: (group) => <span className="chat-session-group-label">{group}</span>,
              }}
              creation={{
                icon: <PlusOutlined />,
                label: '新会话',
                onClick: () => newChat(),
              }}
              menu={(item) => ({
                items: [{
                  key: 'delete',
                  label: '删除会话',
                  danger: true,
                  icon: <DeleteOutlined />,
                }],
                onClick: ({ key }) => {
                  if (key === 'delete') {
                    void removeSession(String(item.key));
                  }
                },
              })}
              onActiveChange={(value) => {
                activateSession(String(value));
              }}
              rootClassName="chat-conversations"
            />
          ) : (
            <div className="chat-session-empty">
              <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无历史会话" />
              <Button type="primary" icon={<PlusOutlined />} onClick={() => newChat()}>
                新建会话
              </Button>
            </div>
          )}
        </div>
      </aside>

      <section className="chat-main-pane">
        <div className="chat-main-head">
          <div className="chat-main-intro">
            <Typography.Title level={4} style={{ margin: 0 }}>
              {activeSession?.title || '新对话'}
            </Typography.Title>
            <Space wrap>
              <Tag color="blue" icon={<RobotOutlined />}>{scopeLabel}</Tag>
              {historyHasMore ? <Tag>当前展示最近 {HISTORY_PAGE_SIZE} 条消息</Tag> : null}
            </Space>
          </div>

          <Space wrap>
            <Button icon={<PlusOutlined />} onClick={() => newChat()}>
              新会话
            </Button>
            <Button icon={<ReloadOutlined />} onClick={() => void refreshConversation()} disabled={!sessionId || isRequesting}>
              刷新历史
            </Button>
            {isRequesting ? (
              <Button danger icon={<StopOutlined />} onClick={abort}>
                停止回复
              </Button>
            ) : null}
            <Popconfirm
              title="确认清空当前会话上下文？"
              onConfirm={() => void clearContext()}
              disabled={!hasPersistedSession || isRequesting}
            >
              <Button disabled={!hasPersistedSession || isRequesting}>
                清空上下文
              </Button>
            </Popconfirm>
            <Popconfirm
              title="确认删除当前会话？"
              onConfirm={() => void removeSession(sessionId)}
              disabled={!sessionId || isRequesting}
            >
              <Button danger icon={<DeleteOutlined />} disabled={!sessionId || isRequesting}>
                删除会话
              </Button>
            </Popconfirm>
          </Space>
        </div>

        <div className="chat-main-stage">
          <div className="chat-transcript">
            {isDefaultMessagesRequesting && bubbleItems.length === 0 ? (
              <div className="chat-loading-state">
                <Spin size="large" />
              </div>
            ) : bubbleItems.length > 0 ? (
              <Bubble.List
                items={bubbleItems}
                role={bubbleRole}
                autoScroll
                rootClassName="chat-bubble-list"
              />
            ) : (
              <div className="chat-empty-wrap">
                <Welcome
                  variant="borderless"
                  icon={<Avatar size={56} icon={<RobotOutlined />} style={{ background: '#1677ff' }} />}
                  title="开始对话"
                  description="上传附件或直接提问"
                />
                <Prompts
                  title="可以从这些问题开始"
                  items={promptItems}
                  wrap
                  fadeIn
                  rootClassName="chat-prompts"
                  onItemClick={({ data }) => {
                    if (typeof data.label === 'string') {
                      submitMessage(data.label);
                    }
                  }}
                />
              </div>
            )}
          </div>

          <div
            className={dragOver ? 'chat-sender-shell drag-over' : 'chat-sender-shell'}
            onDragOver={(event) => {
              event.preventDefault();
              if (!dragOver) setDragOver(true);
            }}
            onDragLeave={(event) => {
              event.preventDefault();
              const nextTarget = event.relatedTarget;
              if (nextTarget instanceof Node && event.currentTarget.contains(nextTarget)) return;
              setDragOver(false);
            }}
            onDrop={(event) => {
              event.preventDefault();
              setDragOver(false);
              if (event.dataTransfer.files.length > 0) {
                void uploadFiles(Array.from(event.dataTransfer.files));
              }
            }}
          >
            {slashMenuVisible ? (
              <div className="chat-slash-menu" role="listbox" aria-label="命令菜单">
                <div className="chat-slash-menu-header">命令</div>
                {slashFiltered.map((item, index) => (
                  <button
                    key={item.cmd}
                    type="button"
                    className={index === slashActiveIdx ? 'chat-slash-menu-item active' : 'chat-slash-menu-item'}
                    role="option"
                    aria-selected={index === slashActiveIdx}
                    onMouseEnter={() => setSlashActiveIdx(index)}
                    onMouseDown={(event) => {
                      event.preventDefault();
                      selectSlashCommand(item.cmd);
                    }}
                  >
                    <span className="chat-slash-menu-cmd">{item.cmd}</span>
                    <span className="chat-slash-menu-desc">{item.desc}</span>
                  </button>
                ))}
              </div>
            ) : null}
            <Sender
              value={draft}
              loading={isRequesting}
              disabled={uploading || !sessionId}
              placeholder={isRequesting ? '模型正在回复...' : '输入消息，输入 / 查看命令'}
              autoSize={{ minRows: 2, maxRows: 6 }}
              onChange={(value) => {
                setDraft(value);
                setSlashHidden(false);
              }}
              onKeyDown={handleSenderKeyDown}
              onFocus={() => {
                if (draft.trimStart().startsWith('/')) setSlashHidden(false);
              }}
              onBlur={() => {
                window.setTimeout(() => setSlashHidden(true), 120);
              }}
              onSubmit={(value) => submitMessage(value)}
              onCancel={abort}
              onPasteFile={(files) => {
                void uploadFiles(Array.from(files));
              }}
              header={attachmentPanelOpen || attachments.length > 0 ? (
                <div className="chat-attachment-panel">
                  <Attachments
                    ref={attachmentsRef}
                    items={attachmentItems}
                    multiple
                    rootClassName="chat-attachments"
                    beforeUpload={(file) => {
                      void uploadFiles([file as File]);
                      return false;
                    }}
                    onRemove={(file) => {
                      setAttachments((prev) => prev.filter((item) => item.file_path !== String(file.uid)));
                      return true;
                    }}
                    placeholder={{
                      icon: uploading ? <LoadingOutlined /> : <PaperClipOutlined />,
                      title: uploading ? '正在上传附件…' : '上传附件',
                      description: '支持图片、视频和文件，可拖拽或点击选择',
                    }}
                  />
                </div>
              ) : false}
              footer={(
                <div className="chat-sender-footer">
                  <Space size={6} wrap>
                    <Button icon={<PaperClipOutlined />} onClick={openAttachmentPanel} loading={uploading}>
                      上传附件
                    </Button>
                    {attachments.length > 0 ? <Tag color="blue">已选择 {attachments.length} 个附件</Tag> : null}
                    {dragOver ? <Tag color="processing">松开以上传附件</Tag> : null}
                  </Space>
                </div>
              )}
            />
          </div>
        </div>
      </section>
    </div>
  );
}
