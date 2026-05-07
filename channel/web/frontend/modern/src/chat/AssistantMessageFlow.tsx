import { Actions, FileCard, ThoughtChain, type BubbleItemType, type FileCardProps, type ThoughtChainItemType } from '@ant-design/x';
import { useEffect, useMemo, useState } from 'react';
import { MarkdownBlock } from './ChatMarkdown';
import { buildChatFileCard } from './fileCards';
import { renderReasoningStepIcon, renderToolStepIcon } from './toolIcons';
import type { AssistantBubbleContent, AssistantMedia, AssistantStep } from '../types';

interface AssistantMessageFlowProps {
  content: AssistantBubbleContent;
  status?: BubbleItemType['status'];
}

function joinClassNames(...values: Array<string | false | null | undefined>): string {
  return values.filter(Boolean).join(' ');
}

function unfoldCodeFence(content?: string): string {
  const text = (content || '').trim();
  const match = text.match(/^```[^\n]*\n([\s\S]*?)\n```$/);
  if (match) return match[1];
  return text;
}

function isLongText(text: string): boolean {
  if (!text.trim()) return false;
  return text.length > 720 || text.split('\n').length > 12;
}

function ToolDetailPanel({
  label,
  text,
  error = false,
}: {
  label: string;
  text: string;
  error?: boolean;
}) {
  const [expanded, setExpanded] = useState(false);
  const longText = isLongText(text);

  return (
    <div className="tool-detail-section">
      <div className="tool-detail-head">
        <div className="tool-detail-label">{label}</div>
        <Actions.Copy text={text} rootClassName="tool-copy-action" aria-label="复制" />
      </div>
      <div
        className={joinClassNames(
          'tool-detail-content-wrap',
          longText && !expanded && 'tool-detail-content-wrap--collapsed',
        )}
      >
        <pre
          className={joinClassNames(
            'tool-detail-content',
            error && 'tool-error-text',
          )}
        >
          {text}
        </pre>
        {longText && !expanded ? <span className="tool-detail-fade" aria-hidden="true" /> : null}
      </div>
      {longText ? (
        <button
          type="button"
          className="tool-detail-toggle"
          onClick={(event) => {
            event.preventDefault();
            event.stopPropagation();
            setExpanded((value) => !value);
          }}
        >
          {expanded ? '收起' : '展开全部'}
        </button>
      ) : null}
    </div>
  );
}

function buildAssistantMediaItems(mediaItems: AssistantMedia[]): FileCardProps[] {
  return mediaItems.map((media, index) => buildChatFileCard({
    key: `${media.url}-${index}`,
    name: media.fileName,
    type: media.type,
    url: media.url,
    openInNewTab: media.type === 'file',
  }));
}

function renderToolContent(step: AssistantStep) {
  const inputText = step.inputMarkdown ? unfoldCodeFence(step.inputMarkdown) : '';
  const outputText = step.outputMarkdown ? unfoldCodeFence(step.outputMarkdown) : '';
  const detailText = !step.inputMarkdown && !step.outputMarkdown && step.markdown
    ? unfoldCodeFence(step.markdown)
    : '';
  const hasDetail = Boolean(inputText || outputText || detailText);

  if (!hasDetail) return undefined;

  return (
    <div className="chat-thought-chain-tool-panels">
      {inputText ? <ToolDetailPanel label="Input" text={inputText} /> : null}
      {outputText ? (
        <ToolDetailPanel
          label={step.status === 'error' ? 'Error' : 'Output'}
          text={outputText}
          error={step.status === 'error'}
        />
      ) : null}
      {!inputText && !outputText && detailText ? (
        <ToolDetailPanel label="Output" text={detailText} />
      ) : null}
    </div>
  );
}

function renderStepMarkdown(step: AssistantStep) {
  if (step.markdown) {
    return (
      <MarkdownBlock
        content={step.markdown}
        loading={step.status === 'loading'}
        className="msg-content chat-thought-chain-markdown"
      />
    );
  }

  return undefined;
}

function buildThoughtChainItems(steps: AssistantStep[]): ThoughtChainItemType[] {
  return steps.map((step) => {
    const toolContent = step.kind === 'tool' ? renderToolContent(step) : undefined;
    const markdownContent = step.kind !== 'tool' ? renderStepMarkdown(step) : undefined;
    const chainContent = toolContent || markdownContent;
    const isCollapsible = (step.kind === 'reasoning' || step.kind === 'tool') && Boolean(chainContent);
    const footer = step.kind === 'reasoning' && step.durationSeconds
      ? `耗时 ${step.durationSeconds.toFixed(1)}s`
      : step.footer;

    let title = step.title;
    if (step.kind === 'tool') {
      title = step.toolName || step.title.replace(/^工具\s*[·:：-]\s*/, '');
    }

    const isCustomIconStep = step.kind === 'tool' || step.kind === 'reasoning';

    return {
      key: step.key,
      title,
      description: step.description,
      status: isCustomIconStep ? undefined : step.status,
      icon: step.kind === 'tool'
        ? renderToolStepIcon(step.toolName || title, step.status)
        : step.kind === 'reasoning'
          ? renderReasoningStepIcon(step.status)
          : undefined,
      content: chainContent,
      footer,
      collapsible: isCollapsible,
      blink: step.status === 'loading',
    };
  });
}

function collectAutoExpandedKeys(steps: AssistantStep[]): string[] {
  return steps
    .filter((step) => (
      (step.kind === 'reasoning' || step.kind === 'tool')
      && (step.status === 'loading' || step.status === 'error' || step.status === 'abort')
    ))
    .map((step) => step.key);
}

export function AssistantMessageFlow({ content, status }: AssistantMessageFlowProps) {
  const isStreaming = status === 'loading' || status === 'updating' || content.streaming;
  const chainItems = useMemo(() => buildThoughtChainItems(content.steps), [content.steps]);
  const mediaItems = useMemo(() => buildAssistantMediaItems(content.media), [content.media]);
  const autoExpandedKeys = useMemo(() => collectAutoExpandedKeys(content.steps), [content.steps]);
  const [expandedKeys, setExpandedKeys] = useState<string[]>(autoExpandedKeys);

  useEffect(() => {
    setExpandedKeys((current) => {
      const availableKeys = new Set(chainItems.map((item) => String(item.key)));
      const next = current.filter((key) => availableKeys.has(key));
      autoExpandedKeys.forEach((key) => {
        if (!next.includes(key)) next.push(key);
      });
      return next;
    });
  }, [autoExpandedKeys, chainItems]);

  return (
    <div className="chat-assistant-card">
      {chainItems.length > 0 ? (
        <div className="agent-steps">
          <ThoughtChain
            items={chainItems}
            line="dashed"
            expandedKeys={expandedKeys}
            onExpand={(keys) => setExpandedKeys(keys.map((key) => String(key)))}
            rootClassName="chat-thought-chain"
          />
        </div>
      ) : null}

      {content.text ? (
        <div className={joinClassNames('answer-content', isStreaming && 'sse-streaming')}>
          <MarkdownBlock content={content.text} loading={isStreaming} className="msg-content chat-main-markdown" withSources />
        </div>
      ) : null}

      {content.media.length > 0 ? (
        <div className="chat-assistant-media">
          <div className="chat-media-list">
            {mediaItems.map((item) => (
              <FileCard
                {...item}
                key={item.key}
                rootClassName="chat-media-file-card"
              />
            ))}
          </div>
        </div>
      ) : null}
    </div>
  );
}
