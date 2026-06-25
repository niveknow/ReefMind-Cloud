export interface DashboardWidget {
  i: string;
  type: 'CaRxPanel' | 'TimeSeriesChart' | 'OutletGrid' | 'ProbeCard' | 'NemoWidget';
  x: number;
  y: number;
  w: number;
  h: number;
  props?: Record<string, any>;
}

export interface DashboardDef {
  id: string;
  name: string;
  description?: string;
  layout: DashboardWidget[];
  theme?: 'modern-dark' | 'classic';
}

export interface StoredLayout {
  id: string;
  name: string;
  def: DashboardDef;
  importedAt: string;
}
