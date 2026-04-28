import { Card, Empty, Spin } from 'antd';
import { useEffect, useRef } from 'react';
import type { EChartsCoreOption, EChartsType } from 'echarts/core';

interface EChartCardProps {
  title: string;
  option: EChartsCoreOption;
  empty?: boolean;
  loading?: boolean;
  className?: string;
  height?: string;
}

type EChartsModule = typeof import('echarts/core');

let echartsLoader: Promise<EChartsModule> | null = null;

function loadECharts() {
  if (!echartsLoader) {
    echartsLoader = Promise.all([
      import('echarts/core'),
      import('echarts/charts'),
      import('echarts/components'),
      import('echarts/renderers'),
    ]).then(([echarts, charts, components, renderers]) => {
      echarts.use([
        charts.BarChart,
        charts.LineChart,
        components.GridComponent,
        components.LegendComponent,
        components.TooltipComponent,
        renderers.CanvasRenderer,
      ]);
      return echarts;
    });
  }
  return echartsLoader;
}

export function EChartCard({ title, option, empty, loading, className, height = '18rem' }: EChartCardProps) {
  const hostRef = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<EChartsType | null>(null);
  const optionRef = useRef<EChartsCoreOption>(option);

  useEffect(() => {
    optionRef.current = option;
    if (!chartRef.current || empty) return;
    chartRef.current.setOption(option, true);
  }, [empty, option]);

  useEffect(() => {
    let disposed = false;
    let resizeObserver: ResizeObserver | undefined;
    if (!hostRef.current || empty) return undefined;

    void loadECharts().then((echarts) => {
      if (disposed || !hostRef.current) return;
      const chart = echarts.init(hostRef.current);
      chartRef.current = chart;
      chart.setOption(optionRef.current, true);
      resizeObserver = new ResizeObserver(() => chart.resize());
      resizeObserver.observe(hostRef.current);
    });

    return () => {
      disposed = true;
      resizeObserver?.disconnect();
      chartRef.current?.dispose();
      chartRef.current = null;
    };
  }, [empty]);

  return (
    <Card className={['echart-card', className].filter(Boolean).join(' ')} title={title}>
      <Spin spinning={Boolean(loading)}>
        {empty ? (
          <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无统计数据" />
        ) : (
          <div ref={hostRef} className="echart-card-canvas" style={{ height }} />
        )}
      </Spin>
    </Card>
  );
}
