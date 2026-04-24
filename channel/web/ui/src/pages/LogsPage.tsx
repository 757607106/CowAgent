import { Button, Card, Space, Typography } from 'antd';
import { useEffect, useRef, useState } from 'react';
import { PageTitle } from '../components/PageTitle';

export default function LogsPage() {
  const [running, setRunning] = useState(false);
  const [lines, setLines] = useState<string[]>([]);
  const sourceRef = useRef<EventSource | null>(null);

  const start = () => {
    if (sourceRef.current) return;
    setRunning(true);
    const source = new EventSource('/api/logs');
    sourceRef.current = source;

    source.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data) as { type: string; content?: string };
        if (payload.type === 'init') {
          const next = String(payload.content || '').split('\n').filter(Boolean);
          setLines(next);
          return;
        }
        if (payload.type === 'line') {
          setLines((prev) => [...prev.slice(-2000), String(payload.content || '')]);
          return;
        }
      } catch {
        setLines((prev) => [...prev.slice(-2000), event.data]);
      }
    };

    source.onerror = () => {
      stop();
    };
  };

  const stop = () => {
    sourceRef.current?.close();
    sourceRef.current = null;
    setRunning(false);
  };

  useEffect(() => {
    start();
    return () => {
      stop();
    };
  }, []);

  return (
    <Card>
      <PageTitle
        title="运行日志"
        description="实时查看 run.log 流式输出。"
        extra={(
          <Space>
            {running ? <Button danger onClick={stop}>停止</Button> : <Button type="primary" onClick={start}>开始</Button>}
            <Button onClick={() => setLines([])}>清空</Button>
          </Space>
        )}
      />
      <Typography.Paragraph
        style={{
          margin: 0,
          whiteSpace: 'pre-wrap',
          fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace',
          fontSize: 12,
          lineHeight: 1.45,
          background: '#111827',
          color: '#d1d5db',
          borderRadius: 8,
          padding: 12,
          minHeight: 520,
          maxHeight: 520,
          overflow: 'auto',
        }}
      >
        {lines.join('') || '暂无日志输出'}
      </Typography.Paragraph>
    </Card>
  );
}
