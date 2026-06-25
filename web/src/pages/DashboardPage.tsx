import { useState, useEffect, useCallback, useMemo } from 'react';
import api from '../api/client';
import NemoWidget from '../components/nemo/NemoWidget';
import TimeSeriesChart from '../components/charts/TimeSeriesChart';
import OutletGrid from '../components/charts/OutletGrid';
import { DashboardGrid } from '../components/dashboard/DashboardGrid';
import { DashboardSelector } from '../components/dashboard/DashboardSelector';
import { DEFAULT_DASHBOARDS } from '../components/dashboard/defaultDashboards';
import { DashboardDef, StoredLayout } from '../types/dashboard';

interface Reading {
  probe_name: string;
  probe_type: string;
  value: number;
  unit: string;
  time?: string;
  did?: string;
}

interface SidebarTab {
  id: string;
  label: string;
  icon: string;
  did?: string;
  probeName?: string;
  href?: string;
}

const PROBE_META: Record<string, { icon: string; color: string; chartColor: string }> = {
  Temp:     { icon: '🌡️', color: 'bg-blue-900/50', chartColor: '#0ea5e9' },
  pH:       { icon: '🧪', color: 'bg-purple-900/50', chartColor: '#a855f7' },
  ORP:      { icon: '⚡', color: 'bg-amber-900/50', chartColor: '#f59e0b' },
  Cond:     { icon: '🧂', color: 'bg-green-900/50', chartColor: '#22c55e' },
  Salinity: { icon: '🧂', color: 'bg-green-900/50', chartColor: '#22c55e' },
};

function getMeta(type: string) {
  return PROBE_META[type] || { icon: '📡', color: 'bg-slate-700/50', chartColor: '#94a3b8' };
}

const getHoursFromDuration = (duration: string): number => {
  if (duration.endsWith('d')) return parseInt(duration) * 24;
  return parseInt(duration);
};

// --- Dashboard storage helpers ---

function getStoredDashboards(): DashboardDef[] {
  try {
    const raw = localStorage.getItem('reefmind_dashboards');
    if (raw) {
      const stored: StoredLayout[] = JSON.parse(raw);
      return stored.map(s => s.def);
    }
  } catch {}
  return [];
}

function storeDashboard(def: DashboardDef) {
  const stored = getStoredDashboards();
  const existing = stored.findIndex(d => d.id === def.id);
  const entry: StoredLayout = { id: def.id, name: def.name, def, importedAt: new Date().toISOString() };
  if (existing >= 0) {
    stored[existing] = def;
    const layouts = JSON.parse(localStorage.getItem('reefmind_dashboards') || '[]') as StoredLayout[];
    layouts[existing] = entry;
    localStorage.setItem('reefmind_dashboards', JSON.stringify(layouts));
  } else {
    const layouts = [...(JSON.parse(localStorage.getItem('reefmind_dashboards') || '[]') as StoredLayout[]), entry];
    localStorage.setItem('reefmind_dashboards', JSON.stringify(layouts));
  }
}

function removeStoredDashboard(id: string) {
  const layouts = JSON.parse(localStorage.getItem('reefmind_dashboards') || '[]') as StoredLayout[];
  const filtered = layouts.filter(l => l.id !== id);
  localStorage.setItem('reefmind_dashboards', JSON.stringify(filtered));
}

export default function DashboardPage() {
  const [summary, setSummary] = useState<{ readings: Reading[]; source?: string }>({ readings: [] });
  const [probeData, setProbeData] = useState<Record<string, any[]>>({});
  const [fusionOutlets, setFusionOutlets] = useState<any[]>([]);
  const [duration, setDuration] = useState('6h');
  const [activeTab, setActiveTab] = useState<string>('overview');
  const [loading, setLoading] = useState(true);
  const [dataSource, setDataSource] = useState<'agent' | 'fusion' | 'none'>('none');

  // Dashboard system state
  const [activeDashboard, setActiveDashboard] = useState<string>('__default__');
  const [importedDashboards, setImportedDashboards] = useState<DashboardDef[]>([]);

  // Available dashboards = defaults + imported
  const allDashboards = useMemo(() => {
    const existingIds = new Set(DEFAULT_DASHBOARDS.map(d => d.id));
    const filteredImported = importedDashboards.filter(d => !existingIds.has(d.id));
    return [...DEFAULT_DASHBOARDS, ...filteredImported];
  }, [importedDashboards]);

  // Load imported dashboards from localStorage
  useEffect(() => {
    setImportedDashboards(getStoredDashboards());
  }, []);

  const currentDashboard = useMemo(() => {
    if (activeDashboard === '__default__') return null;
    return allDashboards.find(d => d.id === activeDashboard) || null;
  }, [activeDashboard, allDashboards]);

  useEffect(() => {
    loadAll();
  }, []);

  // Re-fetch charts when duration changes (mock dashboard mode)
  useEffect(() => {
    if (currentDashboard && dataSource !== 'none' && summary.readings.length > 0) {
      for (const r of summary.readings) {
        if (r.probe_name) {
          loadAgentProbeHistory(r.probe_name);
        }
      }
    }
  }, [duration, activeDashboard]);

  const loadAll = async () => {
    setLoading(true);
    try {
      const statusRes = await api.get('/api/fusion/status').catch(() => null);
      const isConnected = statusRes?.data?.connected;

      let hasAgentData = false;
      let agentReadings: any[] = [];
      try {
        const summaryRes = await api.get('/api/telemetry/summary');
        if (summaryRes.data?.readings?.length > 0) {
          setSummary(summaryRes.data);
          setDataSource('agent');
          hasAgentData = true;
          agentReadings = summaryRes.data.readings;
        }
      } catch { /* no agent */ }

      if (hasAgentData) {
        preloadAgentCharts(agentReadings);
        try {
          const outRes = await api.get('/api/telemetry/outlets');
          if (outRes.data?.outlets?.length > 0) {
            setFusionOutlets(outRes.data.outlets.map((o: any) => ({
              did: o.outlet_name,
              name: o.outlet_name,
              type: 'OUTLET',
              state: o.state_display,
            })));
          }
        } catch { /* ignore */ }
      }

      if (!hasAgentData && isConnected) {
        setDataSource('fusion');
        const readsRes = await api.get('/api/fusion/readings');
        if (readsRes.data?.readings?.length > 0) {
          setSummary(readsRes.data);
        }
        const outRes = await api.get('/api/fusion/outlets').catch(() => null);
        if (outRes?.data?.outlets) {
          setFusionOutlets(outRes.data.outlets);
        }
      }

      if (!hasAgentData && !isConnected) {
        setDataSource('none');
      }
    } catch (e) {
      console.error('Dashboard init error', e);
    } finally {
      setLoading(false);
    }
  };

  const preloadAgentCharts = (readings: Reading[]) => {
    for (const r of readings.slice(0, 4)) {
      const name = r.probe_name;
      if (name) loadAgentProbeHistory(name);
    }
  };

  const loadAgentProbeHistory = async (probeName: string) => {
    try {
      const key = `agent:${probeName}`;
      const res = await api.get(`/api/telemetry/${encodeURIComponent(probeName)}?duration=${duration}`);
      if (res.data?.data?.length > 0) {
        setProbeData(prev => ({ ...prev, [key]: res.data.data }));
      }
    } catch { /* ignore */ }
  };

  // Build dashboard data context for widget rendering
  const dashboardData = useMemo(() => {
    const probes: Record<string, { value: number; unit: string }> = {};
    for (const r of summary.readings) {
      probes[r.probe_name] = { value: r.value, unit: r.unit || '' };
    }

    // CaRx data from available readings
    const carxReading = summary.readings.find(r => r.probe_name === 'CARXpH' || r.probe_name.toLowerCase().includes('carx'));
    const alkReading = summary.readings.find(r => r.probe_name.toLowerCase().includes('alk'));

    // Build charts map from probeData
    const charts: Record<string, any[]> = {};
    for (const r of summary.readings) {
      const key = r.probe_name;
      const dataKey = `agent:${key}`;
      if (probeData[dataKey]) {
        charts[key] = probeData[dataKey];
      }
    }

    return {
      probes,
      outlets: fusionOutlets,
      charts,
      carx: {
        effluentPH: carxReading?.value || 0,
        alkalinity: alkReading?.value || 0,
        co2Pressure: 0,
        bubbleCount: 0,
        status: 'active' as const,
      },
      nemo: {},
    };
  }, [summary, probeData, fusionOutlets]);

  // Sidebar tabs — only used in Default mode
  const sidebarTabs: SidebarTab[] = (() => {
    const tabs: SidebarTab[] = [{ id: 'overview', label: 'Overview', icon: '📊' }];
    if (summary.readings.length > 0) {
      for (const r of summary.readings) {
        const meta = getMeta(r.probe_type);
        tabs.push({
          id: r.did || r.probe_name,
          label: r.probe_name,
          icon: meta.icon,
          did: r.did,
          probeName: r.probe_name,
        });
      }
    }
    tabs.push({ id: 'outlets', label: 'Outlets', icon: '🔌' });
    tabs.push({ id: 'water-tests', label: 'Water Tests', icon: '🧪', href: '/water-tests' });
    tabs.push({ id: 'notes', label: 'Tank Notes', icon: '📝', href: '/notes' });
    tabs.push({ id: 'settings', label: 'Settings', icon: '⚙️', href: '/settings' });
    return tabs;
  })();

  // useEffect for Default mode tab changes
  useEffect(() => {
    if (activeDashboard !== '__default__') return;
    if (dataSource === 'fusion') {
      const activeProbe = sidebarTabs.find(t => t.id === activeTab);
      if (activeProbe?.did) loadFusionProbeHistory(activeProbe.did);
    } else if (dataSource === 'agent') {
      const activeProbe = sidebarTabs.find(t => t.id === activeTab);
      if (activeProbe?.probeName && activeTab !== 'overview' && activeTab !== 'outlets') {
        loadAgentProbeHistory(activeProbe.probeName);
      }
    }
  }, [activeTab, dataSource, duration, activeDashboard]);

  // Preload overview for Default mode
  useEffect(() => {
    if (activeDashboard !== '__default__') return;
    if (dataSource === 'fusion' && summary.readings.length > 0) {
      const probeDids = summary.readings.slice(0, 4).map(r => r.did).filter(Boolean);
      for (const did of probeDids) {
        if (did && !probeData[did]) loadFusionProbeHistory(did);
      }
    }
  }, [summary, dataSource, duration, activeDashboard]);

  const loadFusionProbeHistory = async (did: string) => {
    try {
      const hours = getHoursFromDuration(duration);
      const res = await api.get(`/api/fusion/history/${encodeURIComponent(did)}?hours=${hours}`);
      if (res.data?.data?.length > 0) {
        setProbeData(prev => ({ ...prev, [did]: res.data.data }));
      }
    } catch { /* ignore */ }
  };

  const valueCard = (reading: Reading) => {
    const meta = getMeta(reading.probe_type);
    return (
      <div key={reading.did || reading.probe_name} className={`${meta.color} rounded-lg p-4 border border-slate-700/30`}>
        <div className="text-slate-300 text-sm">{reading.probe_name}</div>
        <div className="text-2xl font-bold text-white mt-1">{reading.value.toFixed(1)}</div>
        <div className="text-slate-400 text-xs">{reading.unit || ''}</div>
      </div>
    );
  };

  const hasData = summary.readings.length > 0 || Object.values(probeData).some(arr => arr.length > 0);
  const overviewProbes = summary.readings.slice(0, 4);

  const getProbeDataKey = (reading: Reading) => {
    if (dataSource === 'fusion') return reading.did || reading.probe_name;
    return `agent:${reading.probe_name}`;
  };

  const activeProbeTab = sidebarTabs.find(t => t.id === activeTab);
  const activeProbeReading = activeProbeTab
    ? summary.readings.find(r => {
        if (dataSource === 'fusion') return r.did === activeProbeTab.did;
        return r.probe_name === activeProbeTab.probeName;
      })
    : null;
  const activeProbeDataKey = activeProbeReading ? getProbeDataKey(activeProbeReading) : '';
  const activeChartData = activeProbeDataKey ? probeData[activeProbeDataKey] : [];

  // --- Handle dashboard import ---
  const handleImportDashboard = useCallback(() => {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.json';
    input.onchange = (e: any) => {
      const file = e.target.files?.[0];
      if (!file) return;
      const reader = new FileReader();
      reader.onload = (ev) => {
        try {
          const def = JSON.parse(ev.target?.result as string) as DashboardDef;
          if (!def.id || !def.name || !def.layout) {
            alert('Invalid dashboard definition: missing id, name, or layout');
            return;
          }
          storeDashboard(def);
          setImportedDashboards(getStoredDashboards());
          setActiveDashboard(def.id);
        } catch {
          alert('Failed to parse dashboard JSON file');
        }
      };
      reader.readAsText(file);
    };
    input.click();
  }, []);

  const handleDeleteDashboard = useCallback((id: string) => {
    removeStoredDashboard(id);
    setImportedDashboards(getStoredDashboards());
    if (activeDashboard === id) setActiveDashboard('__default__');
  }, [activeDashboard]);

  // --- RENDER ---
  return (
    <div className="min-h-screen bg-slate-900 flex">
      {/* Sidebar — only shown in Default mode */}
      {activeDashboard === '__default__' && (
        <nav className="w-56 bg-slate-800 p-4 flex flex-col shrink-0">
          <h2 className="text-teal-400 font-bold text-lg mb-6">ReefMind</h2>
          {sidebarTabs.map(tab => {
            if (tab.href) {
              return (
                <a key={tab.id} href={tab.href}
                  className="text-left px-3 py-2 rounded mb-1 text-slate-300 hover:bg-slate-700 hover:text-white block">
                  {tab.icon} {tab.label}
                </a>
              );
            }
            return (
              <button key={tab.id} onClick={() => setActiveTab(tab.id)}
                className={`text-left px-3 py-2 rounded mb-1 w-full ${
                  activeTab === tab.id ? 'bg-teal-600 text-white' : 'text-slate-300 hover:bg-slate-700'
                }`}>
                {tab.icon} {tab.label}
              </button>
            );
          })}
          <div className="flex-1" />
          {dataSource === 'fusion' && (
            <div className="bg-green-900/30 text-green-300 rounded px-3 py-1 mb-2 text-xs text-center">✅ Live from Fusion</div>
          )}
          {dataSource === 'agent' && (
            <div className="bg-blue-900/30 text-blue-300 rounded px-3 py-1 mb-2 text-xs text-center">📡 Agent data</div>
          )}
          <button onClick={() => { localStorage.clear(); window.location.href = '/login'; }}
            className="text-slate-400 hover:text-red-400 px-3 py-2 text-sm text-left">🚪 Sign Out</button>
        </nav>
      )}

      {/* Main content */}
      <div className="flex-1 p-6 overflow-auto">
        {/* Dashboard selector */}
        <DashboardSelector
          dashboards={allDashboards}
          activeId={activeDashboard}
          onSelect={setActiveDashboard}
          onImport={handleImportDashboard}
          onDelete={handleDeleteDashboard}
        />

        {loading ? (
          <div className="text-slate-400 text-center py-20">Loading dashboard...</div>

        ) : !hasData && activeDashboard === '__default__' ? (
          <div className="text-center py-16">
            <div className="text-6xl mb-6">🐠</div>
            <h2 className="text-2xl font-bold text-white mb-3">Welcome to ReefMind!</h2>
            <p className="text-slate-400 max-w-md mx-auto mb-8">
              Connect Apex Fusion to see your live tank data instantly.
            </p>
            <div className="max-w-sm mx-auto space-y-4 text-left">
              <div className="bg-slate-800 rounded-lg p-4">
                <h3 className="text-teal-400 font-semibold mb-2">🔗 Connect Apex Fusion</h3>
                <p className="text-slate-400 text-sm">Go to <a href="/settings" className="text-teal-400 hover:underline">Settings</a> and enter your Fusion credentials.</p>
              </div>
            </div>
          </div>

        ) : currentDashboard ? (
          /* ---- MOCK DASHBOARD VIEW ---- */
          <div>
            <div className="flex items-center justify-between mb-6">
              <div>
                <h2 className="text-2xl font-bold text-white">{currentDashboard.name}</h2>
                {currentDashboard.description && (
                  <p className="text-slate-400 text-sm mt-1">{currentDashboard.description}</p>
                )}
              </div>
              {currentDashboard.id.startsWith('mock') && (
                <div className="bg-teal-900/30 text-teal-300 text-xs px-3 py-1 rounded-full border border-teal-700/30">
                  Built-in Dashboard
                </div>
              )}
            </div>

            {/* Duration selector for charts */}
            <div className="flex gap-2 mb-4">
              {['1h', '6h', '24h', '30d', '60d', '90d'].map(d => (
                <button key={d} onClick={() => setDuration(d)}
                  className={`px-3 py-1 rounded text-sm transition-all ${
                    duration === d ? 'bg-teal-600 text-white' : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
                  }`}>
                  {d}
                </button>
              ))}
            </div>

            <DashboardGrid layout={currentDashboard.layout} data={dashboardData} />
          </div>

        ) : activeDashboard === '__default__' && (
          /* ---- DEFAULT VIEW ---- */
          <>
            {/* Duration selector */}
            {hasData && activeTab !== 'overview' && activeTab !== 'outlets' && (
              <div className="flex gap-2 mb-4">
                {['1h', '6h', '24h', '30d', '60d', '90d'].map(d => (
                  <button key={d} onClick={() => setDuration(d)}
                    className={`px-3 py-1 rounded text-sm ${duration === d ? 'bg-teal-600 text-white' : 'bg-slate-700 text-slate-300 hover:bg-slate-600'}`}>
                    {d}
                  </button>
                ))}
              </div>
            )}

            {activeTab === 'overview' ? (
              <>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                  {summary.readings.map(r => valueCard(r))}
                </div>
                <div className="space-y-6">
                  {overviewProbes.map(r => {
                    const key = getProbeDataKey(r);
                    const meta = getMeta(r.probe_type);
                    const hasChart = key && probeData[key]?.length > 0;
                    return hasChart ? (
                      <TimeSeriesChart key={key}
                        title={r.probe_name}
                        data={probeData[key]}
                        yLabel={r.unit}
                        color={meta.chartColor} />
                    ) : null;
                  })}
                  <div className="text-xs text-slate-600 mb-1">Outlet data: {fusionOutlets.length} outlets loaded</div>
                  <OutletGrid outlets={fusionOutlets} />
                </div>
              </>
            ) : activeTab === 'outlets' ? (
              <div>
                <h3 className="text-lg font-semibold text-white mb-4">🔌 Outlet States</h3>
                <OutletGrid outlets={fusionOutlets} />
              </div>
            ) : activeProbeTab && activeChartData.length > 0 ? (
              <TimeSeriesChart title={activeProbeTab.label}
                data={activeChartData}
                yLabel={activeProbeReading?.unit || ''}
                color={getMeta(activeProbeReading?.probe_type || '').chartColor}
                large />
            ) : activeProbeTab && activeChartData.length === 0 ? (
              <div className="text-slate-400 text-center py-20">
                <div className="text-4xl mb-4">{activeProbeTab.icon}</div>
                <p className="text-lg text-slate-300 mb-2">{activeProbeTab.label}</p>
                <p className="text-sm">Loading chart data...</p>
              </div>
            ) : null}
          </>
        )}
      </div>

      {/* Nemo chat — only in Default mode for now */}
      {activeDashboard === '__default__' && <NemoWidget />}
    </div>
  );
}
