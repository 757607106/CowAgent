import type { FileCardProps } from '@ant-design/x';
import type { ReactNode } from 'react';

type ChatFileType = NonNullable<FileCardProps['type']>;

interface ChatFileCardSource {
  key: FileCardProps['key'];
  name?: string;
  type?: ChatFileType;
  url?: string;
  description?: ReactNode;
  openInNewTab?: boolean;
}

function normalizeFileName(name?: string, type?: ChatFileType): string {
  if (name?.trim()) return name.trim();
  if (type === 'image') return '图片';
  if (type === 'video') return '视频';
  if (type === 'audio') return '音频';
  return '文件';
}

export function buildChatFileCard(source: ChatFileCardSource): FileCardProps {
  const name = normalizeFileName(source.name, source.type);
  const item: FileCardProps = {
    key: source.key,
    name,
    src: source.url,
    description: source.description,
  };

  if (source.type) {
    item.type = source.type;
  }

  if (item.type === 'image') {
    item.imageProps = { preview: false };
  }

  if (item.type === 'video') {
    item.videoProps = { controls: true, preload: 'metadata' };
  }

  if (item.type === 'audio') {
    item.audioProps = { controls: true, preload: 'metadata' };
  }

  const openUrl = source.openInNewTab ? source.url : undefined;
  if (openUrl) {
    item.onClick = (_info, event) => {
      event.preventDefault();
      event.stopPropagation();
      window.open(openUrl, '_blank', 'noopener,noreferrer');
    };
  }

  return item;
}
