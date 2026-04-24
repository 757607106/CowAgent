import type { BubbleItemType } from '@ant-design/x';
import {
  BulbFilled,
  CheckOutlined,
  CheckCircleFilled,
  CloseCircleFilled,
  CopyOutlined,
  LinkOutlined,
  Loading3QuartersOutlined,
  PauseCircleFilled,
  RightOutlined,
  SettingOutlined,
} from '@ant-design/icons';
import { Typography } from 'antd';
import { useEffect, useState } from 'react';
import { MarkdownBlock } from './ChatMarkdown';
import type { AssistantBubbleContent, AssistantMedia, AssistantStep } from '../types';

interface AssistantMessageFlowProps {
  content: AssistantBubbleContent;
  status?: BubbleItemType['status'];
}

function joinClassNames(...values: Array<string | false | null | undefined>): string {
  return values.filter(Boolean).join(' ');
}

function getToolIcon(status: AssistantStep['status']) {
  if (status === 'loading') return <SettingOutlined spin />;
  if (status === 'error') return <CloseCircleFilled />;
  if (status === 'abort') return <PauseCircleFilled />;
  return <CheckCircleFilled />;
}

function unfoldCodeFence(content?: string): string {
  const text = (content || '').trim();
  const match = text.match(/^```[^\n]*\n([\s\S]*?)\n```$/);
  if (match) return match[1];
  return text;
}

function CopyIconButton({
  text,
  className = 'tool-copy-btn',
}: {
  text: string;
  className?: string;
}) {
  const [copied, setCopied] = useState(false);

  if (!text.trim()) return null;

  return (
    <button
      type="button"
      className={className}
      title={copied ? '已复制' : '复制'}
      onClick={async (event) => {
        event.preventDefault();
        event.stopPropagation();
        try {
          await navigator.clipboard.writeText(text);
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
        <CopyIconButton text={text} />
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

function renderMediaItem(media: AssistantMedia, index: number) {
  if (media.type === 'image') {
    return (
      <img
        key={`${media.url}-${index}`}
        src={media.url}
        alt={media.fileName || 'image'}
        className="chat-media-image"
      />
    );
  }

  if (media.type === 'video') {
    return <video key={`${media.url}-${index}`} src={media.url} controls className="chat-media-video" />;
  }

  return (
    <a
      key={`${media.url}-${index}`}
      href={media.url}
      target="_blank"
      rel="noreferrer"
      className="chat-media-file"
    >
      <LinkOutlined />
      {media.fileName || '下载文件'}
    </a>
  );
}

function ToolStepItem({ step }: { step: AssistantStep }) {
  const hasDetail = Boolean(step.inputMarkdown || step.outputMarkdown || step.markdown);
  const [expanded, setExpanded] = useState(step.status !== 'success');
  const inputText = step.inputMarkdown ? unfoldCodeFence(step.inputMarkdown) : '';
  const outputText = step.outputMarkdown ? unfoldCodeFence(step.outputMarkdown) : '';
  const detailText = !step.inputMarkdown && !step.outputMarkdown && step.markdown
    ? unfoldCodeFence(step.markdown)
    : '';

  useEffect(() => {
    if (step.status === 'loading' || step.status === 'error' || step.status === 'abort') {
      setExpanded(true);
    }
  }, [step.status]);

  return (
    <div
      className={joinClassNames(
        'agent-step',
        'agent-tool-step',
        `chat-step-tool--${step.status}`,
        expanded && 'expanded',
        step.status === 'error' && 'tool-failed',
      )}
    >
      <button
        type="button"
        className="tool-header"
        onClick={() => {
          if (hasDetail) setExpanded((value) => !value);
        }}
      >
        <span className="tool-icon">{getToolIcon(step.status)}</span>
        <span className="tool-name">{step.toolName || step.title.replace(/^工具\s·\s/, '')}</span>
        {step.footer ? <span className="tool-time">{step.footer}</span> : null}
        <span className="tool-chevron">{hasDetail ? <RightOutlined /> : null}</span>
      </button>

      {hasDetail ? (
        <div className="tool-detail">
          {step.inputMarkdown ? (
            <ToolDetailPanel label="Input" text={inputText} />
          ) : null}

          {step.outputMarkdown ? (
            <ToolDetailPanel
              label={step.status === 'error' ? 'Error' : 'Output'}
              text={outputText}
              error={step.status === 'error'}
            />
          ) : null}

          {!step.inputMarkdown && !step.outputMarkdown && step.markdown ? (
            <ToolDetailPanel label="Output" text={detailText} />
          ) : null}
        </div>
      ) : null}
    </div>
  );
}

function ReasoningStepItem({ step }: { step: AssistantStep }) {
  const loading = step.status === 'loading';
  const [expanded, setExpanded] = useState(loading);

  useEffect(() => {
    if (loading) setExpanded(true);
  }, [loading]);

  return (
    <div className={joinClassNames('agent-step', 'agent-thinking-step', loading && 'chat-step-think--loading', expanded && 'expanded')}>
      <button type="button" className="thinking-header" onClick={() => setExpanded((value) => !value)}>
        <span className="thinking-bulb"><BulbFilled /></span>
        <span className="thinking-summary">{loading ? '深度思考中' : '已深度思考'}</span>
        <span className="thinking-chevron"><RightOutlined /></span>
      </button>
      <div className="thinking-full">
        {!loading && step.durationSeconds ? (
          <div className="thinking-duration">耗时 {step.durationSeconds.toFixed(1)}s</div>
        ) : null}
        {step.markdown ? (
          <MarkdownBlock content={step.markdown} loading={loading} className="msg-content" />
        ) : (
          <Typography.Text type="secondary">思考中…</Typography.Text>
        )}
      </div>
    </div>
  );
}

function ContentStepItem({ step }: { step: AssistantStep }) {
  if (step.kind === 'phase' || step.kind === 'status') {
    return (
      <div className={joinClassNames('agent-step', 'chat-phase-line', `chat-phase-line--${step.status}`)}>
        <span>{step.markdown || step.title}</span>
      </div>
    );
  }

  return (
    <div className={joinClassNames('agent-step', 'agent-content-step', `chat-step-content--${step.kind}`, `chat-step-content--${step.status}`)}>
      {step.markdown ? (
        <div className="agent-content-body">
          <MarkdownBlock
            content={step.markdown}
            loading={step.status === 'loading'}
            className="msg-content"
            withSources={step.kind === 'output'}
          />
        </div>
      ) : null}
    </div>
  );
}

export function AssistantMessageFlow({ content, status }: AssistantMessageFlowProps) {
  const isStreaming = status === 'loading' || status === 'updating' || content.streaming;
  const hasSteps = content.steps.length > 0;

  return (
    <div className="chat-assistant-card">
      {hasSteps ? (
        <div className="agent-steps">
          {content.steps.map((step) => {
            if (step.kind === 'reasoning') {
              return <ReasoningStepItem key={step.key} step={step} />;
            }
            if (step.kind === 'tool') {
              return <ToolStepItem key={step.key} step={step} />;
            }
            return <ContentStepItem key={step.key} step={step} />;
          })}
        </div>
      ) : null}

      {(content.text || isStreaming) ? (
        <div className={joinClassNames('answer-content', isStreaming && 'sse-streaming')}>
          {content.text ? (
            <MarkdownBlock content={content.text} loading={isStreaming} className="msg-content chat-main-markdown" withSources />
          ) : (
            <div className="chat-response-loading">
              <Loading3QuartersOutlined spin />
              <span>生成中…</span>
            </div>
          )}
        </div>
      ) : null}

      {content.media.length > 0 ? (
        <div className="chat-assistant-media">
          <div className="chat-media-list">
            {content.media.map(renderMediaItem)}
          </div>
        </div>
      ) : null}
    </div>
  );
}
