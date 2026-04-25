import { CodeHighlighter, Mermaid, Sources, type SourcesProps } from '@ant-design/x';
import { XMarkdown, type ComponentProps } from '@ant-design/x-markdown';
import { isValidElement, type ReactNode, useMemo } from 'react';

export interface MarkdownBlockProps {
  content: string;
  loading?: boolean;
  className?: string;
  withSources?: boolean;
}

function joinClassNames(...values: Array<string | false | null | undefined>): string {
  return values.filter(Boolean).join(' ');
}

function getNodeText(children: ReactNode): string {
  if (children === null || children === undefined) return '';
  if (typeof children === 'string' || typeof children === 'number' || typeof children === 'boolean') {
    return String(children);
  }
  if (Array.isArray(children)) {
    return children.map((item) => getNodeText(item)).join('');
  }
  if (isValidElement(children)) {
    return getNodeText((children.props as { children?: ReactNode }).children);
  }
  return '';
}

function normalizeLanguage(lang?: string): string {
  const value = (lang || '').trim().toLowerCase();
  if (!value) return 'text';
  return value.split(/\s+/)[0].replace(/^language-/, '');
}

function sanitizeMarkdownForSources(content: string): string {
  return content
    .replace(/```[\s\S]*?```/g, '')
    .replace(/`[^`]*`/g, '');
}

function safeUrl(raw: string): string | null {
  try {
    const url = new URL(raw);
    if (url.protocol === 'http:' || url.protocol === 'https:') {
      return url.toString();
    }
  } catch {
    return null;
  }
  return null;
}

function fallbackSourceTitle(url: string): string {
  try {
    const target = new URL(url);
    return target.hostname.replace(/^www\./, '') || url;
  } catch {
    return url;
  }
}

const VIDEO_EXT_RE = /\.(?:mp4|webm|mov|avi|mkv)$/i;

function isVideoUrl(url?: string): boolean {
  if (!url) return false;
  const safe = safeUrl(url);
  if (!safe) return false;
  try {
    return VIDEO_EXT_RE.test(new URL(safe).pathname);
  } catch {
    return false;
  }
}

export function extractMarkdownSources(content: string): NonNullable<SourcesProps['items']> {
  if (!content.trim()) return [];

  const text = sanitizeMarkdownForSources(content);
  const items: NonNullable<SourcesProps['items']> = [];
  const seen = new Set<string>();

  const markdownLinkPattern = /\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g;
  for (const match of text.matchAll(markdownLinkPattern)) {
    const full = match[0] || '';
    const offset = match.index || 0;
    if (offset > 0 && text[offset - 1] === '!') continue;
    if (!full) continue;

    const url = safeUrl(match[2] || '');
    if (!url || seen.has(url)) continue;
    seen.add(url);
    items.push({
      key: url,
      title: (match[1] || '').trim() || fallbackSourceTitle(url),
      url,
      description: url,
    });
  }

  const bareUrlPattern = /(^|[\s(])(https?:\/\/[^\s<)]+)(?=$|[\s),.!?])/g;
  for (const match of text.matchAll(bareUrlPattern)) {
    const url = safeUrl(match[2] || '');
    if (!url || seen.has(url)) continue;
    seen.add(url);
    items.push({
      key: url,
      title: fallbackSourceTitle(url),
      url,
      description: url,
    });
  }

  return items.slice(0, 8);
}

function MarkdownCodeRenderer({ children, lang, block, streamStatus, className }: ComponentProps) {
  const code = getNodeText(children).replace(/\n$/, '');
  const language = normalizeLanguage(lang);

  if (!block) {
    return <code className={className}>{children}</code>;
  }

  if (language === 'mermaid' && streamStatus === 'done') {
    return (
      <div className="chat-markdown-mermaid">
        <Mermaid header={null}>{code}</Mermaid>
      </div>
    );
  }

  const highlightLanguage = language === 'mermaid' ? 'markdown' : language;
  return (
    <div className="chat-markdown-code">
      <CodeHighlighter lang={highlightLanguage}>{code}</CodeHighlighter>
    </div>
  );
}

function MarkdownLinkRenderer({ children, href, className }: ComponentProps<{ href?: string }>) {
  const safe = safeUrl(href || '');

  if (safe && isVideoUrl(safe)) {
    return (
      <div className="chat-markdown-video">
        <video controls preload="metadata" className="chat-markdown-video-player">
          <source src={safe} />
        </video>
        <a href={safe} target="_blank" rel="noopener noreferrer" className="chat-markdown-video-link">
          {getNodeText(children) || fallbackSourceTitle(safe)}
        </a>
      </div>
    );
  }

  return (
    <a href={href} target="_blank" rel="noopener noreferrer" className={className}>
      {children}
    </a>
  );
}

const MARKDOWN_COMPONENTS = {
  a: MarkdownLinkRenderer,
  code: MarkdownCodeRenderer,
};

export function MarkdownBlock({
  content,
  loading = false,
  className,
  withSources = false,
}: MarkdownBlockProps) {
  const sourceItems = useMemo(
    () => (withSources ? extractMarkdownSources(content) : []),
    [content, withSources],
  );

  return (
    <div className={joinClassNames('chat-markdown-shell', className)}>
      <XMarkdown
        content={content}
        openLinksInNewTab
        escapeRawHtml
        components={MARKDOWN_COMPONENTS}
        rootClassName={joinClassNames('chat-markdown', className)}
        streaming={loading ? { hasNextChunk: true, enableAnimation: true, tail: false } : undefined}
      />
      {withSources && sourceItems.length > 0 ? (
        <div className="chat-sources-wrap">
          <Sources
            title={`引用 ${sourceItems.length}`}
            items={sourceItems}
            defaultExpanded={false}
            expandIconPosition="end"
            rootClassName="chat-sources"
          />
        </div>
      ) : null}
    </div>
  );
}
