import {
  AbstractChatProvider,
  type MessageInfo,
  XRequest,
  type SSEOutput,
  type XRequestOptions,
} from '@ant-design/x-sdk';
import type {
  AssistantBubbleContent,
  AssistantMedia,
  AssistantStep,
  ChatAttachment,
} from '../types';

const MAX_TOOL_RESULT_LENGTH = 4000;
const CONTEXT_CLEARED_TEXT = '— 以上内容已从上下文中移除 —';

export interface CowAgentChatRequest {
  session_id: string;
  message: string;
  attachments?: ChatAttachment[];
  timestamp?: string;
  agent_id?: string;
  binding_id?: string;
}

export type CowAgentChatRole = 'user' | 'assistant' | 'system' | 'divider';

export interface CowAgentChatMessage {
  role: CowAgentChatRole;
  createdAt: number;
  text?: string;
  attachments?: ChatAttachment[];
  content?: AssistantBubbleContent;
}

export interface StreamEventPayload {
  type: string;
  content?: unknown;
  message?: unknown;
  tool?: unknown;
  arguments?: unknown;
  result?: unknown;
  status?: unknown;
  execution_time?: unknown;
  has_tool_calls?: unknown;
  file_name?: unknown;
}

function createEmptyAssistantContent(streaming = true): AssistantBubbleContent {
  return {
    text: '',
    steps: [],
    media: [],
    streaming,
  };
}

function cloneAssistantContent(content?: AssistantBubbleContent): AssistantBubbleContent {
  return {
    text: content?.text || '',
    steps: [...(content?.steps || [])],
    media: [...(content?.media || [])],
    streaming: content?.streaming ?? true,
  };
}

function createAssistantMessage(content?: Partial<AssistantBubbleContent>): CowAgentChatMessage {
  return {
    role: 'assistant',
    createdAt: Date.now(),
    content: {
      ...createEmptyAssistantContent(true),
      ...content,
      steps: [...(content?.steps || [])],
      media: [...(content?.media || [])],
    },
  };
}

function ensureAssistantMessage(originMessage?: CowAgentChatMessage): CowAgentChatMessage {
  if (originMessage?.role === 'assistant') {
    return {
      ...originMessage,
      content: cloneAssistantContent(originMessage.content),
    };
  }
  return createAssistantMessage();
}

function normalizeTimestamp(value: unknown): number {
  const numeric = Number(value || 0);
  if (!Number.isFinite(numeric) || numeric <= 0) return Date.now();
  return numeric < 1_000_000_000_000 ? numeric * 1000 : numeric;
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

function toJsonString(value: unknown): string | null {
  if (value === undefined || value === null || value === '') return null;
  if (typeof value === 'string') {
    const text = value.trim();
    if (!text) return null;
    try {
      return JSON.stringify(JSON.parse(text), null, 2);
    } catch {
      return null;
    }
  }
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return null;
  }
}

function toCodeBlock(content: string, lang: string): string {
  return `\`\`\`${lang}\n${content}\n\`\`\``;
}

function looksLikeMarkdown(text: string): boolean {
  if (!text) return false;
  return /(^|\n)(#{1,6}\s|[-*+]\s|\d+\.\s|>\s)|\[[^\]]+\]\([^)]*\)|```|!\[[^\]]*\]\([^)]*\)/.test(text);
}

function formatToolInputMarkdown(value: unknown): string {
  const json = toJsonString(value);
  if (json) return toCodeBlock(json, 'json');
  const text = asText(value).trim();
  if (!text) return '_无输入参数_';
  return looksLikeMarkdown(text) ? text : toCodeBlock(text, 'text');
}

function formatToolOutputMarkdown(value: unknown): string {
  const text = asText(value).trim();
  if (!text) return '_无输出_';

  const sliced = text.length > MAX_TOOL_RESULT_LENGTH
    ? `${text.slice(0, MAX_TOOL_RESULT_LENGTH)}\n...（输出过长，已截断）`
    : text;

  const json = toJsonString(sliced);
  if (json) return toCodeBlock(json, 'json');
  return looksLikeMarkdown(sliced) ? sliced : toCodeBlock(sliced, 'text');
}

function getToolStatusText(status: AssistantStep['status']): string {
  if (status === 'loading') return '执行中';
  if (status === 'success') return '执行完成';
  if (status === 'error') return '执行失败';
  return '已中止';
}

function finalizeRunningReasoning(steps: AssistantStep[], status: AssistantStep['status']) {
  for (let idx = steps.length - 1; idx >= 0; idx -= 1) {
    const step = steps[idx];
    if (step.kind !== 'reasoning' || step.status !== 'loading') continue;
    const durationSeconds = step.startedAt
      ? Number(Math.max((Date.now() - step.startedAt) / 1000, 0).toFixed(1))
      : step.durationSeconds;
    steps[idx] = {
      ...step,
      status,
      description: status === 'loading' ? '思考中...' : status === 'success' ? '思考完成' : status === 'abort' ? '思考已中止' : '思考失败',
      durationSeconds,
    };
    return;
  }
}

function findLoadingToolIndex(steps: AssistantStep[], toolName?: string): number {
  for (let idx = steps.length - 1; idx >= 0; idx -= 1) {
    const step = steps[idx];
    if (step.kind !== 'tool' || step.status !== 'loading') continue;
    if (!toolName || step.toolName === toolName) return idx;
  }
  return -1;
}

function finalizeRunningTool(steps: AssistantStep[], status: AssistantStep['status']) {
  const targetIndex = findLoadingToolIndex(steps);
  if (targetIndex === -1) return;
  const step = steps[targetIndex];
  steps[targetIndex] = {
    ...step,
    status,
    description: getToolStatusText(status),
  };
}

function createStepKey(prefix: string, suffix?: string): string {
  const seed = suffix || `${Date.now()}-${Math.random().toString(16).slice(2, 8)}`;
  return `${prefix}-${seed}`;
}

function parseStreamEvent(chunk?: SSEOutput): StreamEventPayload | null {
  if (!chunk) return null;

  if ('type' in chunk && typeof (chunk as StreamEventPayload).type === 'string') {
    return chunk as unknown as StreamEventPayload;
  }

  const raw = chunk.data;
  if (typeof raw === 'string') {
    const text = raw.trim();
    if (!text) return null;
    if (text === '[DONE]') return { type: 'done' };
    try {
      return JSON.parse(text) as StreamEventPayload;
    } catch {
      return { type: 'delta', content: text };
    }
  }

  if (raw && typeof raw === 'object' && 'type' in raw) {
    return raw as StreamEventPayload;
  }

  return null;
}

function applyStreamPayload(message: CowAgentChatMessage, payload: StreamEventPayload): CowAgentChatMessage {
  const next = ensureAssistantMessage(message);
  const content = cloneAssistantContent(next.content);
  const steps = [...content.steps];

  switch (payload.type) {
    case 'reasoning': {
      const chunkText = asText(payload.content);
      const lastStep = steps.at(-1);
      if (lastStep?.kind === 'reasoning' && lastStep.status === 'loading') {
        steps[steps.length - 1] = {
          ...lastStep,
          markdown: `${lastStep.markdown || ''}${chunkText}`,
          description: '思考中...',
        };
      } else {
        steps.push({
          key: createStepKey('reasoning'),
          kind: 'reasoning',
          title: '深度思考',
          description: '思考中...',
          markdown: chunkText,
          status: 'loading',
          startedAt: Date.now(),
        });
      }
      content.steps = steps;
      content.streaming = true;
      break;
    }

    case 'tool_start': {
      finalizeRunningReasoning(steps, 'success');
      finalizeRunningTool(steps, 'success');
      const toolName = asText(payload.tool) || 'tool';
      steps.push({
        key: createStepKey('tool'),
        kind: 'tool',
        title: `工具 · ${toolName}`,
        toolName,
        description: '执行中',
        inputMarkdown: formatToolInputMarkdown(payload.arguments),
        status: 'loading',
      });
      content.steps = steps;
      content.streaming = true;
      break;
    }

    case 'tool_end': {
      finalizeRunningReasoning(steps, 'success');
      const toolName = asText(payload.tool) || undefined;
      const toolIndex = findLoadingToolIndex(steps, toolName);
      const executionTime = Number(payload.execution_time || 0);
      const status = payload.status === 'error' ? 'error' : 'success';

      if (toolIndex === -1) {
        steps.push({
          key: createStepKey('tool-end'),
          kind: 'tool',
          title: `工具 · ${toolName || 'tool'}`,
          toolName,
          description: getToolStatusText(status),
          outputMarkdown: formatToolOutputMarkdown(payload.result),
          footer: executionTime > 0 ? `耗时 ${executionTime.toFixed(2)}s` : undefined,
          status,
        });
      } else {
        const current = steps[toolIndex];
        steps[toolIndex] = {
          ...current,
          status,
          description: getToolStatusText(status),
          outputMarkdown: formatToolOutputMarkdown(payload.result),
          footer: executionTime > 0 ? `耗时 ${executionTime.toFixed(2)}s` : current.footer,
        };
      }

      content.steps = steps;
      content.streaming = true;
      break;
    }

    case 'phase': {
      steps.push({
        key: createStepKey('phase'),
        kind: 'phase',
        title: '阶段进展',
        description: '运行状态',
        markdown: asText(payload.content),
        status: 'success',
      });
      content.steps = steps;
      content.streaming = true;
      break;
    }

    case 'delta': {
      finalizeRunningReasoning(steps, 'success');
      content.steps = steps;
      content.text = `${content.text}${asText(payload.content)}`;
      content.streaming = true;
      break;
    }

    case 'text': {
      finalizeRunningReasoning(steps, 'success');
      content.steps = steps;
      content.text = payload.content ? asText(payload.content) : content.text;
      content.streaming = true;
      break;
    }

    case 'message_end': {
      if (payload.has_tool_calls && content.text.trim()) {
        steps.push({
          key: createStepKey('stage-output'),
          kind: 'output',
          title: '阶段回答',
          description: '工具执行后的阶段结论',
          markdown: content.text,
          status: 'success',
        });
        content.text = '';
      }
      content.steps = steps;
      content.streaming = true;
      break;
    }

    case 'image':
    case 'video':
    case 'file': {
      const media: AssistantMedia = {
        type: payload.type,
        url: asText(payload.content),
        fileName: asText(payload.file_name) || undefined,
      };
      content.media = [...content.media, media];
      content.streaming = true;
      break;
    }

    case 'cancelled': {
      finalizeRunningReasoning(steps, 'abort');
      finalizeRunningTool(steps, 'abort');
      steps.push({
        key: createStepKey('cancelled'),
        kind: 'status',
        title: '已停止回复',
        description: '本次流式回复已中止',
        markdown: asText(payload.content) || '当前回复已手动停止。',
        status: 'abort',
      });
      content.steps = steps;
      content.streaming = false;
      break;
    }

    case 'error': {
      finalizeRunningReasoning(steps, 'error');
      finalizeRunningTool(steps, 'error');
      steps.push({
        key: createStepKey('error'),
        kind: 'status',
        title: '回复失败',
        description: '本次流式请求发生错误',
        markdown: asText(payload.message) || asText(payload.content) || '流式请求失败。',
        status: 'error',
      });
      content.steps = steps;
      content.streaming = false;
      break;
    }

    case 'done': {
      finalizeRunningReasoning(steps, 'success');
      finalizeRunningTool(steps, 'success');
      content.steps = steps;
      content.text = payload.content ? asText(payload.content) : content.text;
      content.streaming = false;
      break;
    }

    default:
      break;
  }

  next.content = content;
  return next;
}

function finalizeAssistantMessage(message: CowAgentChatMessage, status: AssistantStep['status']): CowAgentChatMessage {
  const next = ensureAssistantMessage(message);
  const content = cloneAssistantContent(next.content);
  const steps = [...content.steps];
  finalizeRunningReasoning(steps, status);
  finalizeRunningTool(steps, status);
  content.steps = steps;
  content.streaming = false;
  next.content = content;
  return next;
}

function createFallbackAssistantMessage(originMessage: CowAgentChatMessage | undefined, error: Error): CowAgentChatMessage {
  const status = error.name === 'AbortError' ? 'abort' : 'error';
  const next = finalizeAssistantMessage(
    originMessage?.role === 'assistant' ? originMessage : createAssistantMessage(),
    status,
  );
  const content = cloneAssistantContent(next.content);
  content.steps = [...content.steps, {
    key: createStepKey('fallback'),
    kind: 'status',
    title: status === 'abort' ? '已停止回复' : '回复失败',
    description: status === 'abort' ? '本次流式回复已中止' : '网络或服务异常',
    markdown: status === 'abort' ? '你已手动停止当前回复。' : (error.message || '网络异常，请稍后再试。'),
    status,
  }];
  next.content = content;
  return next;
}

function normalizeAttachment(item: any): ChatAttachment | null {
  if (!item || typeof item !== 'object') return null;
  const fileType = item.file_type === 'image' || item.file_type === 'video' || item.file_type === 'file'
    ? item.file_type
    : 'file';
  return {
    file_path: String(item.file_path || item.preview_url || item.url || item.file_name || Date.now()),
    file_name: String(item.file_name || item.name || '附件'),
    file_type: fileType,
    preview_url: item.preview_url || item.url || undefined,
  };
}

function parseHistoryAssistantContent(row: any): AssistantBubbleContent {
  const steps: AssistantStep[] = [];
  let text = String(row.content || '');

  if (Array.isArray(row.steps) && row.steps.length > 0) {
    const contentSteps = row.steps.filter((item: any) => item.type === 'content');
    const lastContent = contentSteps.at(-1);
    if (!text && lastContent?.content) text = String(lastContent.content);

    row.steps.forEach((step: any, index: number) => {
      if (step.type === 'content' && step !== lastContent) {
        steps.push({
          key: `history-content-${index}`,
          kind: 'output',
          title: '阶段回答',
          description: '中间产出',
          markdown: asText(step.content),
          status: 'success',
        });
        return;
      }

      if (step.type === 'thinking') {
        steps.push({
          key: `history-thinking-${index}`,
          kind: 'reasoning',
          title: '深度思考',
          description: '思考完成',
          markdown: asText(step.content),
          status: 'success',
        });
        return;
      }

      if (step.type === 'tool') {
        const status = step.status === 'error' ? 'error' : 'success';
        const executionTime = Number(step.execution_time || 0);
        steps.push({
          key: `history-tool-${index}`,
          kind: 'tool',
          title: `工具 · ${step.name || 'tool'}`,
          toolName: String(step.name || 'tool'),
          description: getToolStatusText(status),
          inputMarkdown: formatToolInputMarkdown(step.arguments),
          outputMarkdown: formatToolOutputMarkdown(step.result),
          footer: executionTime > 0 ? `耗时 ${executionTime.toFixed(2)}s` : undefined,
          status,
        });
      }
    });
  } else {
    if (row.reasoning) {
      steps.push({
        key: 'history-reasoning',
        kind: 'reasoning',
        title: '深度思考',
        description: '思考完成',
        markdown: asText(row.reasoning),
        status: 'success',
      });
    }

    if (Array.isArray(row.tool_calls)) {
      row.tool_calls.forEach((tool: any, index: number) => {
        const status = tool.status === 'error' ? 'error' : 'success';
        steps.push({
          key: `history-tool-${index}`,
          kind: 'tool',
          title: `工具 · ${tool.name || 'tool'}`,
          toolName: String(tool.name || 'tool'),
          description: getToolStatusText(status),
          inputMarkdown: formatToolInputMarkdown(tool.arguments),
          outputMarkdown: formatToolOutputMarkdown(tool.result),
          status,
        });
      });
    }
  }

  return {
    text,
    steps,
    media: [],
    streaming: false,
  };
}

function createHistoryMessageId(row: any, index: number, prefix: string): string {
  const seq = row?._seq ?? row?.created_at ?? `${Date.now()}-${index}`;
  return `${prefix}-${seq}-${index}`;
}

export function parseHistoryMessages(rows: any[], contextStartSeq = 0): MessageInfo<CowAgentChatMessage>[] {
  const messages: MessageInfo<CowAgentChatMessage>[] = [];
  let dividerInserted = false;

  rows.forEach((row, index) => {
    if (contextStartSeq > 0 && !dividerInserted && row?._seq !== undefined && Number(row._seq) >= contextStartSeq) {
      dividerInserted = true;
      messages.push({
        id: `history-divider-${contextStartSeq}`,
        status: 'success',
        message: {
          role: 'divider',
          text: CONTEXT_CLEARED_TEXT,
          createdAt: normalizeTimestamp(row.created_at),
        },
      });
    }

    if (row.role === 'user') {
      const attachments = Array.isArray(row.attachments)
        ? row.attachments.map(normalizeAttachment).filter(Boolean) as ChatAttachment[]
        : [];
      if (!String(row.content || '').trim() && attachments.length === 0) return;
      messages.push({
        id: createHistoryMessageId(row, index, 'history-user'),
        status: 'success',
        message: {
          role: 'user',
          text: String(row.content || ''),
          attachments,
          createdAt: normalizeTimestamp(row.created_at),
        },
      });
      return;
    }

    if (row.role === 'assistant') {
      const content = parseHistoryAssistantContent(row);
      if (!content.text && content.steps.length === 0 && content.media.length === 0) return;
      messages.push({
        id: createHistoryMessageId(row, index, 'history-assistant'),
        status: 'success',
        message: {
          role: 'assistant',
          content,
          createdAt: normalizeTimestamp(row.created_at),
        },
      });
      return;
    }

    if (String(row.content || '').trim()) {
      messages.push({
        id: createHistoryMessageId(row, index, 'history-system'),
        status: 'success',
        message: {
          role: 'system',
          text: String(row.content || ''),
          createdAt: normalizeTimestamp(row.created_at),
        },
      });
    }
  });

  if (contextStartSeq > 0 && !dividerInserted) {
    messages.push({
      id: `history-divider-${contextStartSeq}`,
      status: 'success',
      message: {
        role: 'divider',
        text: CONTEXT_CLEARED_TEXT,
        createdAt: Date.now(),
      },
    });
  }

  return messages;
}

export function createContextDividerMessage(): MessageInfo<CowAgentChatMessage> {
  return {
    id: `context-divider-${Date.now()}`,
    status: 'success',
    message: {
      role: 'divider',
      text: CONTEXT_CLEARED_TEXT,
      createdAt: Date.now(),
    },
  };
}

export function createAssistantPlaceholderMessage(): CowAgentChatMessage {
  return createAssistantMessage({ streaming: true });
}

export function createAssistantErrorMessage(originMessage: CowAgentChatMessage | undefined, error: Error): CowAgentChatMessage {
  return createFallbackAssistantMessage(originMessage, error);
}

export function extractAssistantReply(message?: CowAgentChatMessage): string {
  if (!message || message.role !== 'assistant') return '';
  return message.content?.text || '';
}

async function cowAgentStreamFetch(
  baseURL: RequestInfo | URL,
  options: XRequestOptions<CowAgentChatRequest, SSEOutput>,
): Promise<Response> {
  const bootstrapResponse = await fetch(baseURL, {
    method: options.method || 'POST',
    body: options.body,
    headers: options.headers,
    credentials: 'same-origin',
    signal: options.signal,
  });

  const bootstrapPayload = await bootstrapResponse.json();
  if (!bootstrapResponse.ok || bootstrapPayload?.status === 'error') {
    throw new Error(String(bootstrapPayload?.message || `请求失败：${bootstrapResponse.status}`));
  }

  const requestId = bootstrapPayload?.request_id;
  if (!requestId) {
    return new Response(JSON.stringify(bootstrapPayload), {
      status: 200,
      headers: {
        'Content-Type': 'application/json',
      },
    });
  }

  const streamResponse = await fetch(`/stream?request_id=${encodeURIComponent(String(requestId))}`, {
    method: 'GET',
    credentials: 'same-origin',
    headers: {
      Accept: 'text/event-stream',
    },
    signal: options.signal,
  });

  if (!streamResponse.ok) {
    const reason = await streamResponse.text().catch(() => '');
    throw new Error(reason || `流式请求失败：${streamResponse.status}`);
  }

  const headers = new Headers(streamResponse.headers);
  headers.set('Content-Type', headers.get('Content-Type') || 'text/event-stream');
  headers.set('X-CowAgent-Request-Id', String(requestId));

  return new Response(streamResponse.body, {
    status: streamResponse.status,
    statusText: streamResponse.statusText,
    headers,
  });
}

class CowAgentChatProvider extends AbstractChatProvider<CowAgentChatMessage, CowAgentChatRequest, SSEOutput> {
  transformParams(
    requestParams: Partial<CowAgentChatRequest>,
    options: XRequestOptions<CowAgentChatRequest, SSEOutput, CowAgentChatMessage>,
  ): CowAgentChatRequest {
    if (typeof requestParams !== 'object') {
      throw new Error('requestParams must be an object');
    }

    return {
      ...(options?.params || {}),
      ...(requestParams || {}),
      attachments: requestParams.attachments || [],
      stream: true,
    } as CowAgentChatRequest;
  }

  transformLocalMessage(requestParams: Partial<CowAgentChatRequest>): CowAgentChatMessage {
    return {
      role: 'user',
      text: requestParams.message || '',
      attachments: requestParams.attachments || [],
      createdAt: Date.now(),
    };
  }

  transformMessage(info: {
    originMessage?: CowAgentChatMessage;
    chunk: SSEOutput;
    chunks: SSEOutput[];
    status: 'local' | 'loading' | 'updating' | 'success' | 'error' | 'abort';
    responseHeaders: Headers;
  }): CowAgentChatMessage {
    const { originMessage, chunk, chunks, status } = info;

    if (!chunk && Array.isArray(chunks)) {
      if (originMessage?.role === 'assistant') {
        return finalizeAssistantMessage(originMessage, status === 'success' ? 'success' : 'error');
      }
      return createAssistantMessage({ streaming: false });
    }

    const payload = parseStreamEvent(chunk);
    if (!payload) {
      return originMessage?.role === 'assistant'
        ? ensureAssistantMessage(originMessage)
        : createAssistantMessage();
    }

    return applyStreamPayload(originMessage || createAssistantMessage(), payload);
  }
}

export function createCowAgentChatProvider() {
  return new CowAgentChatProvider({
    request: XRequest<CowAgentChatRequest, SSEOutput, CowAgentChatMessage>('/message', {
      manual: true,
      fetch: cowAgentStreamFetch,
    }),
  });
}
