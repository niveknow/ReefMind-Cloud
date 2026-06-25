import React from 'react';
import { DashboardWidget } from '../../types/dashboard';
import { CaRxPanel } from './CaRxPanel';
import { ProbeCard } from './ProbeCard';
import TimeSeriesChart from '../charts/TimeSeriesChart';
import OutletGrid from '../charts/OutletGrid';
import NemoWidget from '../nemo/NemoWidget';

interface WidgetRendererProps {
  widget: DashboardWidget;
  data: any;
}

export const WidgetRenderer: React.FC<WidgetRendererProps> = ({ widget, data }) => {
  switch (widget.type) {
    case 'CaRxPanel':
      return <CaRxPanel {...(data.carx || { effluentPH: 0, alkalinity: 0, co2Pressure: 0, bubbleCount: 0, status: 'idle' })} />;
    case 'TimeSeriesChart':
      return <TimeSeriesChart
        title={widget.props?.title || 'Chart'}
        data={data.charts?.[widget.props?.id || ''] || []}
        yLabel={widget.props?.yLabel || ''}
        color={widget.props?.color || '#0ea5e9'}
      />;
    case 'OutletGrid':
      return <OutletGrid outlets={data.outlets || []} />;
    case 'ProbeCard':
      return <ProbeCard {...(widget.props as any)} value={data.probes?.[widget.props?.probeId]?.value || '—'} />;
    case 'NemoWidget':
      return <NemoWidget {...(data.nemo || {})} />;
    default:
      return <div className="text-red-500">Unknown Widget: {widget.type}</div>;
  }
};
