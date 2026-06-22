import ReactECharts from 'echarts-for-react';

interface DataPoint {
  time: string;
  value: number;
}

interface Props {
  title: string;
  data: DataPoint[];
  yLabel: string;
  color: string;
  large?: boolean;
}

export default function TimeSeriesChart({ title, data, yLabel, color, large }: Props) {
  const option = {
    backgroundColor: 'transparent',
    title: {
      text: title,
      textStyle: { color: '#e2e8f0', fontSize: 14 },
    },
    tooltip: {
      trigger: 'axis',
      textStyle: { color: '#fff' },
      backgroundColor: 'rgba(30, 41, 59, 0.9)',
      borderColor: '#475569',
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      top: large ? '8%' : '15%',
      containLabel: true,
    },
    xAxis: {
      type: 'time',
      axisLine: { lineStyle: { color: '#475569' } },
      axisLabel: { color: '#94a3b8', fontSize: 11 },
      splitLine: { show: false },
    },
    yAxis: {
      type: 'value',
      name: yLabel,
      nameTextStyle: { color: '#94a3b8' },
      axisLabel: { color: '#94a3b8', fontSize: 11 },
      splitLine: { lineStyle: { color: '#334155', type: 'dashed' } },
    },
    series: [{
      type: 'line',
      data: data.map(d => [d.time, d.value]),
      smooth: true,
      symbol: 'none',
      lineStyle: { width: 2, color },
      areaStyle: {
        color: {
          type: 'linear',
          x: 0, y: 0, x2: 0, y2: 1,
          colorStops: [
            { offset: 0, color: color + '40' },
            { offset: 1, color: color + '05' },
          ],
        },
      },
    }],
  };

  return (
    <div className={`bg-slate-800 rounded-lg p-4 ${large ? '' : ''}`}>
      <ReactECharts option={option} style={{ height: large ? 400 : 250 }} />
    </div>
  );
}
