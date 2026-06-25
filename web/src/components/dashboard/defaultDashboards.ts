import { DashboardDef } from '../../types/dashboard';

export const DEFAULT_DASHBOARDS: DashboardDef[] = [
  {
    id: 'mock1',
    name: 'Mock 1 — CaRx Focus',
    description: 'Calcium Reactor panel front and center with supporting charts',
    theme: 'modern-dark',
    layout: [
      { i: 'carx-1', type: 'CaRxPanel', x: 0, y: 0, w: 12, h: 2 },
      { i: 'chart-ph', type: 'TimeSeriesChart', x: 0, y: 2, w: 6, h: 3, props: { id: 'pH', title: 'pH', color: '#a855f7' } },
      { i: 'chart-alk', type: 'TimeSeriesChart', x: 6, y: 2, w: 6, h: 3, props: { id: 'CARXpH', title: 'Effluent pH', color: '#0ea5e9' } },
      { i: 'probe-temp', type: 'ProbeCard', x: 0, y: 5, w: 3, h: 1, props: { probeId: 'Temp', label: 'Temperature', unit: '°F' } },
      { i: 'probe-sal', type: 'ProbeCard', x: 3, y: 5, w: 3, h: 1, props: { probeId: 'Salinity', label: 'Salinity', unit: 'PPT' } },
      { i: 'probe-orp', type: 'ProbeCard', x: 6, y: 5, w: 3, h: 1, props: { probeId: 'ORP', label: 'ORP', unit: 'mV' } },
      { i: 'outlets', type: 'OutletGrid', x: 0, y: 6, w: 12, h: 3 },
    ],
  },
  {
    id: 'mock2',
    name: 'Mock 2 — Full View',
    description: 'All probes, water tests, and outlets in one view',
    theme: 'modern-dark',
    layout: [
      { i: 'probe-temp', type: 'ProbeCard', x: 0, y: 0, w: 3, h: 1, props: { probeId: 'Temp', label: 'Temperature', unit: '°F' } },
      { i: 'probe-ph', type: 'ProbeCard', x: 3, y: 0, w: 3, h: 1, props: { probeId: 'pH', label: 'pH', unit: 'pH' } },
      { i: 'probe-orp', type: 'ProbeCard', x: 6, y: 0, w: 3, h: 1, props: { probeId: 'ORP', label: 'ORP', unit: 'mV' } },
      { i: 'probe-sal', type: 'ProbeCard', x: 9, y: 0, w: 3, h: 1, props: { probeId: 'Salinity', label: 'Salinity', unit: 'PPT' } },
      { i: 'chart-ph', type: 'TimeSeriesChart', x: 0, y: 1, w: 6, h: 3, props: { id: 'pH', title: 'pH', color: '#a855f7' } },
      { i: 'chart-temp', type: 'TimeSeriesChart', x: 6, y: 1, w: 6, h: 3, props: { id: 'Temp', title: 'Temperature', color: '#0ea5e9' } },
      { i: 'outlets', type: 'OutletGrid', x: 0, y: 4, w: 12, h: 3 },
    ],
  },
  {
    id: 'mock3',
    name: 'Mock 3 — Water Chemistry',
    description: 'Water tests, probe trends, and notes at a glance',
    theme: 'modern-dark',
    layout: [
      { i: 'carx-1', type: 'CaRxPanel', x: 0, y: 0, w: 6, h: 2 },
      { i: 'chart-ph', type: 'TimeSeriesChart', x: 6, y: 0, w: 6, h: 2, props: { id: 'pH', title: 'pH', color: '#a855f7' } },
      { i: 'chart-orp', type: 'TimeSeriesChart', x: 0, y: 2, w: 6, h: 2, props: { id: 'ORP', title: 'ORP', color: '#f59e0b' } },
      { i: 'chart-temp', type: 'TimeSeriesChart', x: 6, y: 2, w: 6, h: 2, props: { id: 'Temp', title: 'Temperature', color: '#0ea5e9' } },
      { i: 'probe-ph', type: 'ProbeCard', x: 0, y: 4, w: 3, h: 1, props: { probeId: 'pH', label: 'pH', unit: 'pH' } },
      { i: 'probe-temp', type: 'ProbeCard', x: 3, y: 4, w: 3, h: 1, props: { probeId: 'Temp', label: 'Temp', unit: '°F' } },
      { i: 'probe-orp', type: 'ProbeCard', x: 6, y: 4, w: 3, h: 1, props: { probeId: 'ORP', label: 'ORP', unit: 'mV' } },
      { i: 'probe-sal', type: 'ProbeCard', x: 9, y: 4, w: 3, h: 1, props: { probeId: 'Salinity', label: 'Salinity', unit: 'PPT' } },
      { i: 'outlets', type: 'OutletGrid', x: 0, y: 5, w: 12, h: 3 },
    ],
  },
];
