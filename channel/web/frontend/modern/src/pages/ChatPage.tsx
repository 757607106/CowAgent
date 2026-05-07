import {
  Actions,
  Attachments,
  Bubble,
  Conversations,
  FileCard,
  Sender,
  Suggestion,
  Welcome,
  type BubbleItemType,
  type FileCardProps,
} from '@ant-design/x';
import {
  ArrowDownOutlined,
  BulbOutlined,
  DeleteOutlined,
  LoadingOutlined,
  PaperClipOutlined,
  PlusOutlined,
  ReloadOutlined,
  StopOutlined,
  UserOutlined,
} from '@ant-design/icons';
import { App, Avatar, Button, Dropdown, Empty, Flex, Space, Spin, Tag, Tooltip, Typography } from 'antd';
import { useCallback, useEffect, useMemo, useRef, useState, type ComponentRef, type KeyboardEvent as ReactKeyboardEvent } from 'react';
import {
  type CoreAgentChatMessage,
  type CoreAgentChatRequest,
  createAssistantErrorMessage,
  createAssistantPlaceholderMessage,
  createCoreAgentChatProvider,
  extractAssistantReply,
  parseHistoryMessages,
} from '../chat/CoreAgentChatProvider';
import { AssistantMessageFlow } from '../chat/AssistantMessageFlow';
import { MarkdownBlock } from '../chat/ChatMarkdown';
import { DEFAULT_AGENT_ID, DEFAULT_AGENT_NAME, useRuntimeScope } from '../context/runtime';
import {
  HISTORY_PAGE_SIZE,
  buildConversationItems,
  buildConversationKey,
  createSessionId,
  getScopeLabel,
  persistSessionId,
  readStoredSessionId,
} from '../chat/sessionState';
import { buildChatFileCard } from '../chat/fileCards';
import { ReasoningIcon } from '../chat/toolIcons';
import { asAttachment, api } from '../services/api';
import { scopeBody } from '../services/http';
import type { ChatAttachment, SessionItem } from '../types';
import { useXChat, type SSEOutput } from '@ant-design/x-sdk';
import { avatarOptionByKey } from '../utils/avatar';

const SenderSwitch = Sender.Switch;
const SenderHeader = Sender.Header;
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
  { cmd: '/version', desc: '查看版本' },
] as const;

function buildSuggestionItems(query?: string) {
  const text = (query || '').trimStart().toLowerCase();
  if (!text.startsWith('/')) return [];

  return SLASH_COMMANDS
    .filter((item) => item.cmd.toLowerCase().startsWith(text))
    .map((item) => ({
      value: item.cmd,
      label: item.cmd,
      extra: item.desc,
    }));
}

function formatAgentTriggerLabel(label: string): string {
  return label
    .replace(/（.*$/, '')
    .replace(/\s*\(.*\)$/, '')
    .trim() || '助手';
}

function formatClock(value: number): string {
  return new Intl.DateTimeFormat('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
  }).format(value);
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

function buildUserFileCardItems(attachments: ChatAttachment[]): FileCardProps[] {
  return attachments.map((attachment) => buildChatFileCard({
    key: attachment.file_path,
    name: attachment.file_name,
    type: attachment.file_type,
    url: attachment.preview_url || attachment.file_path,
    openInNewTab: attachment.file_type === 'file',
  }));
}

function buildBubbleItems(
  messages: ReturnType<typeof useXChat<CoreAgentChatMessage, CoreAgentChatMessage, CoreAgentChatRequest, SSEOutput>>['messages'],
  scopeLabel: string,
): BubbleItemType[] {
  return messages.map((item) => {
    const isAssistant = item.message.role === 'assistant';
    const assistantContent = isAssistant ? item.message.content : undefined;
    const assistantText = assistantContent?.text || '';
    const assistantHasContent = Boolean(
      assistantText.trim()
      || assistantContent?.steps.length
      || assistantContent?.media.length,
    );
    const assistantStreaming = Boolean(
      isAssistant
      && (item.status === 'loading' || item.status === 'updating' || assistantContent?.streaming),
    );

    return {
      key: item.id,
      role: item.message.role === 'assistant' ? 'assistant' : item.message.role === 'divider' ? 'system' : item.message.role,
      content: item.message,
      status: item.status,
      loading: isAssistant && assistantStreaming && !assistantHasContent,
      streaming: assistantStreaming,
      extraInfo: {
        createdAt: item.message.createdAt,
        scopeLabel,
        copyText: assistantText,
        canCopy: item.message.role === 'assistant' && item.status === 'success' && Boolean(assistantText.trim()),
      },
    };
  });
}



export default function ChatPage() {
  const app = App.useApp();
  const { scope, agentOptions, setAgentScope } = useRuntimeScope();
  const provider = useMemo(() => createCoreAgentChatProvider(), []);
  const attachmentsRef = useRef<ComponentRef<typeof Attachments>>(null);
  const transcriptRef = useRef<HTMLDivElement>(null);
  const pendingTitleRef = useRef<{
    conversationKey: string;
    sessionId: string;
    userMessage: string;
  } | null>(null);
  const previousRequestingRef = useRef(false);
  const [suggestionOpen, setSuggestionOpen] = useState(false);

  const [sessionId, setSessionId] = useState<string>(() => readStoredSessionId(scope));
  const [sessions, setSessions] = useState<SessionItem[]>([]);
  const [sessionsLoading, setSessionsLoading] = useState(false);
  const [attachments, setAttachments] = useState<ChatAttachment[]>([]);
  const [attachmentPanelOpen, setAttachmentPanelOpen] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [historyHasMore, setHistoryHasMore] = useState(false);
  const [draft, setDraft] = useState('');
  const [dragOver, setDragOver] = useState(false);
  const [deepThink, setDeepThink] = useState<boolean | null>(null);
  const [autoScrollEnabled, setAutoScrollEnabled] = useState(true);
  const inputHistoryRef = useRef<string[]>([]);
  const historyIndexRef = useRef(-1);
  const historyDraftRef = useRef('');

  const fallbackScopeLabel = useMemo(() => getScopeLabel(scope), [scope.agentId, scope.bindingId]);
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
    onRequest,
    abort,
    isRequesting,
    isDefaultMessagesRequesting,
  } = useXChat<CoreAgentChatMessage, CoreAgentChatMessage, CoreAgentChatRequest, SSEOutput>({
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
  const suggestionItems = useMemo(() => buildSuggestionItems(draft), [draft]);
  const agentSelectorOptions = useMemo(
    () => (agentOptions.length > 0
      ? agentOptions
      : [{ label: DEFAULT_AGENT_NAME, value: DEFAULT_AGENT_ID }]),
    [agentOptions],
  );
  const selectedAgentValue = useMemo(
    () => scope.agentId || DEFAULT_AGENT_ID,
    [scope.agentId],
  );
  const selectedAgentOption = useMemo(
    () => agentSelectorOptions.find((item) => item.value === selectedAgentValue),
    [agentSelectorOptions, selectedAgentValue],
  );
  const selectedAgentLabel = useMemo(
    () => selectedAgentOption?.label || fallbackScopeLabel,
    [selectedAgentOption, fallbackScopeLabel],
  );
  const assistantAvatarSrc = useMemo(
    () => avatarOptionByKey(selectedAgentOption?.avatar_key).src,
    [selectedAgentOption],
  );
  const scopeLabel = scope.bindingId ? fallbackScopeLabel : selectedAgentLabel;
  const bubbleItems = useMemo(() => buildBubbleItems(messages, scopeLabel), [messages, scopeLabel]);
  const agentMenuItems = useMemo(
    () => agentSelectorOptions.map((item) => ({
      key: item.value,
      icon: <Avatar size={20} src={avatarOptionByKey(item.avatar_key).src} />,
      label: item.label,
    })),
    [agentSelectorOptions],
  );

  const scrollToBottom = useCallback(() => {
    const node = transcriptRef.current;
    if (!node) return;
    node.scrollTop = node.scrollHeight;
    setAutoScrollEnabled(true);
  }, []);

  useEffect(() => {
    let cancelled = false;
    void api.getConfig()
      .then((data) => {
        if (!cancelled) setDeepThink(Boolean(data.enable_thinking ?? false));
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!autoScrollEnabled) return;
    const node = transcriptRef.current;
    if (!node) return;
    requestAnimationFrame(() => {
      node.scrollTop = node.scrollHeight;
    });
  }, [autoScrollEnabled, bubbleItems.length, messages]);

  const activateSession = useCallback((nextSessionId: string) => {
    persistSessionId(scope, nextSessionId);
    setSessionId(nextSessionId);
    setAutoScrollEnabled(true);
    setSuggestionOpen(false);
    setDraft('');
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
    setAutoScrollEnabled(true);
    setSuggestionOpen(false);
    setDraft('');
    setAutoScrollEnabled(true);
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

  const revealAttachmentPanel = useCallback(() => {
    setAttachmentPanelOpen(true);

    window.setTimeout(() => {
      attachmentsRef.current?.nativeElement?.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
    }, 120);
  }, []);

  const openAttachmentPanel = useCallback(() => {
    if (attachmentPanelOpen) {
      setAttachmentPanelOpen(false);
      return;
    }

    revealAttachmentPanel();

    if (uploading || attachments.length > 0) {
      return;
    }

    // Wait for Sender.Header motion to settle, then open the native picker.
    window.setTimeout(() => {
      attachmentsRef.current?.select({ multiple: true });
    }, 180);
  }, [attachmentPanelOpen, attachments.length, revealAttachmentPanel, uploading]);

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
    setSuggestionOpen(false);
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
      ...(deepThink === null ? {} : { enable_thinking: deepThink }),
      timestamp: new Date().toISOString(),
      ...scopeBody(scope),
    });
  }, [attachments, conversationKey, deepThink, onRequest, scope.agentId, scope.bindingId, sessionId, sessions]);

  const handleSenderKeyDown = useCallback((event: ReactKeyboardEvent) => {
    if ((event.nativeEvent as KeyboardEvent).isComposing) return;
    if (event.key === 'ArrowUp') {
      if (inputHistoryRef.current.length === 0 || draft.includes('\n') || suggestionOpen) return;
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
      if (historyIndexRef.current < 0 || draft.includes('\n') || suggestionOpen) return;
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
  }, [draft, suggestionOpen]);

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
      variant: 'borderless' as const,
      avatar: <Avatar className="chat-avatar-user" icon={<UserOutlined />} />,
      footerPlacement: 'outer-end' as const,
      footer: (_content: unknown, info: { extraInfo?: Record<string, unknown> }) => (
        <span className="chat-bubble-time">{formatClock(Number(info.extraInfo?.createdAt || Date.now()))}</span>
      ),
      contentRender: (content: CoreAgentChatMessage) => (
        <div className="chat-user-stack">
          {content.attachments?.length ? (
            <div className="chat-user-attachments">
              <FileCard.List
                items={buildUserFileCardItems(content.attachments)}
                size="small"
                overflow="wrap"
                rootClassName="chat-user-file-list"
              />
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
      avatar: <Avatar className="chat-avatar-assistant" src={assistantAvatarSrc} />,
      footerPlacement: 'outer-start' as const,
      footer: (_content: unknown, info: { extraInfo?: Record<string, unknown> }) => (
        <div className="chat-bubble-meta">
          <span>{String(info.extraInfo?.scopeLabel || scopeLabel)}</span>
          <span>{formatClock(Number(info.extraInfo?.createdAt || Date.now()))}</span>
          {info.extraInfo?.canCopy ? (
            <Actions.Copy
              text={String(info.extraInfo.copyText || '')}
              rootClassName="chat-bubble-copy-action"
              aria-label="复制回复"
            />
          ) : null}
        </div>
      ),
      contentRender: (content: CoreAgentChatMessage, info: { status?: BubbleItemType['status'] }) => {
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
      contentRender: (content: CoreAgentChatMessage) => {
        if (content.role === 'divider') {
          return <div className="chat-divider-chip">{content.text || '上下文已清空'}</div>;
        }
        return <Typography.Text>{content.text || asText(content)}</Typography.Text>;
      },
    },
  }), [scopeLabel, assistantAvatarSrc]);

  return (
    <div className="chat-page">
      <aside className="chat-session-pane">
        <div className="chat-session-head">
          <div>
            <Typography.Title level={5} className="chat-pane-title">会话</Typography.Title>
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
            <Avatar size={30} src={assistantAvatarSrc} className="chat-active-agent-avatar" />
            <div className="chat-active-agent-copy">
              <Typography.Title level={5} className="chat-pane-title" style={{ fontSize: 14, fontWeight: 600, margin: 0, lineHeight: '1.3' }}>
                {activeSession?.title || '新对话'}
              </Typography.Title>
              <div className="chat-active-agent-meta">
                <span>{formatAgentTriggerLabel(scopeLabel)}</span>
                <span>{isRequesting ? '正在响应…' : '在线'}</span>
                {historyHasMore ? (
                  <span style={{ color: 'var(--text-tertiary)' }}>最近 {HISTORY_PAGE_SIZE} 条</span>
                ) : null}
              </div>
            </div>
          </div>

          {(!autoScrollEnabled && bubbleItems.length > 0) || isRequesting ? (
            <Space wrap>
              {!autoScrollEnabled && bubbleItems.length > 0 ? (
                <Button size="small" icon={<ArrowDownOutlined />} onClick={scrollToBottom}>
                  回到底部
                </Button>
              ) : null}
              {isRequesting ? (
                <Button size="small" danger icon={<StopOutlined />} onClick={abort}>
                  停止
                </Button>
              ) : null}
            </Space>
          ) : null}
        </div>

        <div className="chat-main-stage">
          <div
            ref={transcriptRef}
            className="chat-transcript"
            onScroll={(event) => {
              const target = event.currentTarget;
              const distanceToBottom = target.scrollHeight - target.scrollTop - target.clientHeight;
              setAutoScrollEnabled(distanceToBottom < 120);
            }}
          >
            {isDefaultMessagesRequesting && bubbleItems.length === 0 ? (
              <div className="chat-loading-state">
                <Spin size="large" />
              </div>
            ) : bubbleItems.length > 0 ? (
              <Bubble.List
                items={bubbleItems}
                role={bubbleRole}
                autoScroll={autoScrollEnabled}
                rootClassName="chat-bubble-list"
              />
            ) : (
              <div className="chat-empty-wrap">
                <Welcome
                  variant="borderless"
                  icon={<Avatar size={48} src={assistantAvatarSrc} className="chat-welcome-avatar" />}
                  title={`与 ${formatAgentTriggerLabel(scopeLabel)} 对话`}
                />
              </div>
            )}
          </div>

          <div className="chat-sender-wrap">
            <Suggestion
              items={suggestionItems}
              open={suggestionOpen && suggestionItems.length > 0}
              onOpenChange={setSuggestionOpen}
              onSelect={(value) => {
                setDraft(value);
                setSuggestionOpen(false);
              }}
              rootClassName="chat-command-suggestion"
            >
              {({ onTrigger, onKeyDown }) => (
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
                <Sender
                  value={draft}
                  loading={isRequesting}
                  disabled={uploading || !sessionId}
                  placeholder={isRequesting ? '模型正在回复...' : '输入消息，输入 / 查看命令'}
                  autoSize={{ minRows: 2, maxRows: 5 }}
                  onChange={(value) => {
                    setDraft(value);
                    const shouldOpen = value.trimStart().startsWith('/') && buildSuggestionItems(value).length > 0;
                    setSuggestionOpen(shouldOpen);
                    onTrigger(shouldOpen ? value : false);
                  }}
                  onKeyDown={(event) => {
                    if (suggestionOpen && suggestionItems.length > 0) {
                      onKeyDown(event);
                      if (event.defaultPrevented) return;
                    }
                    handleSenderKeyDown(event);
                  }}
                  onSubmit={(value) => submitMessage(value)}
                  onCancel={abort}
                  onPasteFile={(files) => {
                    void uploadFiles(Array.from(files));
                  }}

                  header={(
                    <SenderHeader
                      open={attachmentPanelOpen}
                      forceRender
                      title={uploading ? '正在上传附件…' : attachments.length > 0 ? `附件 (${attachments.length})` : '附件'}
                      className="chat-sender-header"
                      classNames={{
                        content: 'chat-sender-header-content',
                      }}
                      onOpenChange={setAttachmentPanelOpen}
                    >
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
                    </SenderHeader>
                  )}
                  footer={(actionNode) => (
                    <Flex justify="space-between" align="center" gap={10} wrap className="chat-sender-footer-bar">
                      <Flex align="center" gap={8} wrap>
                        <Button
                          type="text"
                          icon={<PaperClipOutlined />}
                          aria-label={attachmentPanelOpen ? '收起附件面板' : '上传附件'}
                          title={attachmentPanelOpen ? '收起附件面板' : '上传附件'}
                          onClick={openAttachmentPanel}
                          loading={uploading}
                          style={{ color: attachmentPanelOpen ? 'var(--color-primary)' : 'var(--text-secondary)' }}
                        />
                        <SenderSwitch
                          value={deepThink ?? false}
                          icon={<ReasoningIcon />}
                          checkedChildren="深度思考：开"
                          unCheckedChildren="深度思考：关"
                          onChange={(checked) => setDeepThink(Boolean(checked))}
                        />
                        <Dropdown
                          trigger={['click']}
                          menu={{
                            selectable: true,
                            selectedKeys: [selectedAgentValue],
                            items: agentMenuItems,
                            onClick: ({ key }) => setAgentScope(String(key)),
                          }}
                        >
                          <span>
                            <SenderSwitch
                              value={false}
                              icon={<Avatar size={20} src={assistantAvatarSrc} />}
                            >
                              {formatAgentTriggerLabel(selectedAgentLabel)}
                            </SenderSwitch>
                          </span>
                        </Dropdown>
                        {attachments.length > 0 ? <Tag color="blue">已选 {attachments.length}</Tag> : null}
                        {dragOver ? <Tag color="processing">松开上传</Tag> : null}
                      </Flex>
                      <Flex align="center" gap={8}>
                        {actionNode}
                      </Flex>
                    </Flex>
                  )}
                  suffix={false}
                />
                </div>
              )}
            </Suggestion>
          </div>
        </div>
      </section>

    </div>
  );
}
