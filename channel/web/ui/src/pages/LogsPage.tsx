import { Button, Card, Space, Tag, Typography } from 'antd';
import { useEffect, useMemo, useRef, useState } from 'react';
import { PageTitle } from '../components/PageTitle';

const MAX_LOG_LINES = 2000;

function toLogLines(value: string): string[] {
  return value.match(/[^\r\n]+/g) || [];
}

export default function LogsPage() {
  const [running, setRunning] = useState(false);
  const [lines, setLines] = useState<string[]>([]);
  const sourceRef = useRef<EventSource | null>(null);
  const consoleRef = useRef<HTMLPreElement | null>(null);

  const stop = () => {
    sourceRef.current?.close();
    sourceRef.current = null;
    setRunning(false);
  };

  const start = () => {
    if (sourceRef.current) return;
    setRunning(true);
    const source = new EventSource('/api/logs');
    sourceRef.current = source;

    source.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data) as { type: string; content?: string };
        if (payload.type === 'init') {
          setLines(toLogLines(String(payload.content || '')).slice(-MAX_LOG_LINES));
          return;
        }
        if (payload.type === 'line') {
          const nextLines = toLogLines(String(payload.content || ''));
          setLines((prev) => [...prev, ...(nextLines.length ? nextLines : [''])].slice(-MAX_LOG_LINES));
          return;
        }
      } catch {
        setLines((prev) => [...prev, ...toLogLines(event.data)].slice(-MAX_LOG_LINES));
      }
    };

    source.onerror = () => {
      stop();
    };
  };

  useEffect(() => {
    start();
    return () => {
      stop();
    };
  }, []);

  useEffect(() => {
    const node = consoleRef.current;
    if (node) node.scrollTop = node.scrollHeight;
  }, [lines]);

  const logText = useMemo(
    () => lines.join('\n') || (running ? '等待新的日志事件。' : '暂无日志输出。'),
    [lines, running],
  );

  return (
    <Card className="logs-simple-card">
      <PageTitle
        title="运行日志"
        description="实时查看 run.log 流式输出。"
        extra={(
          <Space wrap>
            <Tag color={running ? 'blue' : 'default'}>
              {running ? '实时监听' : '已停止'}
            </Tag>
            {running ? (
              <Button danger onClick={stop}>停止</Button>
            ) : (
              <Button type="primary" onClick={start}>开始</Button>
            )}
            <Button onClick={() => setLines([])}>清空</Button>
          </Space>
        )}
      />
      <Typography.Text type="secondary" className="logs-simple-meta">
        最近 {lines.length} 行，最多保留 {MAX_LOG_LINES} 行
      </Typography.Text>
      <pre ref={consoleRef} className="logs-console">
        {logText}
      </pre>
    </Card>
  );
}
