import { useState, useEffect } from 'react';
import api from '../api/client';
import NemoWidget from '../components/nemo/NemoWidget';
import TimeSeriesChart from '../components/charts/TimeSeriesChart';
import OutletGrid from '../components/charts/OutletGrid';

interface Reading {
  probe_name: string;
  probe_type: string;
  value: number;
  unit: string;
  time?: string;
  did?: string;
}

interface FusionStatus {
  connected: boolean;
  fusion_user: string;
  fusion_apex_id: string;
  discovered: boolean;
}

interface SidebarTab {
  id: string;
  label: string;
  icon: string;
  did?: string;          // probe DID for history fetching
  probeName?: string;    // display name from reading
}

// Map probe types to display icons/colors
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

export default function DashboardPage() {
  const [summary, setSummary] = useState<{ readings: Reading[]; source?: string }>({ readings: [] });
  const [probeData, setProbeData] = useState<Record<string, any[]>>({});
  const [fusionOutlets, setFusionOutlets] = useState<any[]>([]);
  const [duration, setDuration] = useState('6h');
  const [activeTab, setActiveTab] = useState<string>('overview');
  const [loading, setLoading] = useState(true);
  const [dataSource, setDataSource] = useState<'agent' | 'fusion' | 'none'>('none');

  useEffect(() => {
    loadAll();
  }, []);

  const loadAll = async () => {
    setLoading(true);
    try {
      const statusRes = await api.get('/api/fusion/status').catch(() => null);
      const isConnected = statusRes?.data?.connected;

      // Try agent data first (collected from Fusion polling into InfluxDB)
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
        // Preload overview chart data from InfluxDB telemetry
        preloadAgentCharts(agentReadings);
        // Load outlets from InfluxDB
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

      // Fall back to Fusion live
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
    // Preload history for top probes shown on overview
    for (const r of readings.slice(0, 4)) {
      const name = r.probe_name;
      if (name) {
        loadAgentProbeHistory(name);
      }
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

  // Build sidebar tabs dynamically from readings
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
    return tabs;
  })();

  // Load probe history for the active probe tab
  useEffect(() => {
    if (dataSource === 'fusion') {
      const activeProbe = sidebarTabs.find(t => t.id === activeTab);
      if (activeProbe?.did) {
        loadFusionProbeHistory(activeProbe.did);
      }
    } else if (dataSource === 'agent') {
      const activeProbe = sidebarTabs.find(t => t.id === activeTab);
      if (activeProbe?.probeName) {
        loadAgentProbeHistory(activeProbe.probeName);
      }
    }
  }, [activeTab, dataSource]);

  // Also preload overview charts
  useEffect(() => {
    if (dataSource === 'fusion' && summary.readings.length > 0) {
      // Preload history for top probes shown in overview
      const probeDids = summary.readings.slice(0, 4).map(r => r.did).filter(Boolean);
      for (const did of probeDids) {
        if (did && !probeData[did]) {
          loadFusionProbeHistory(did);
        }
      }
    }
  }, [summary, dataSource]);

  const loadFusionProbeHistory = async (did: string) => {
    try {
      const hours = parseInt(duration.replace('h', '').replace('d', '24'));
      const res = await api.get(`/api/fusion/history/${encodeURIComponent(did)}?hours=${hours}`);
      if (res.data?.data?.length > 0) {
        setProbeData(prev => ({ ...prev, [did]: res.data.data }));
      }
    } catch { /* ignore */ }
  };

  // ---- Render helpers ----

  const valueCard = (reading: Reading) => {
    const meta = getMeta(reading.probe_type);
    return (
      <div key={reading.did || reading.probe_name} className={`${meta.color} rounded-lg p-4`}>
        <div className="text-slate-300 text-sm">{reading.probe_name}</div>
        <div className="text-2xl font-bold text-white mt-1">
          {reading.value.toFixed(1)}
        </div>
        <div className="text-slate-400 text-xs">{reading.unit || ''}</div>
      </div>
    );
  };

  const hasData = summary.readings.length > 0 ||
    Object.values(probeData).some(arr => arr.length > 0);

  // Determine what charts to show in overview (top 4 probes)
  const overviewProbes = summary.readings.slice(0, 4);

  // Build a probe-data key: fusion uses did, agent uses probe_name
  const getProbeDataKey = (reading: Reading) => {
    if (dataSource === 'fusion') return reading.did || reading.probe_name;
    return `agent:${reading.probe_name}`;
  };

  // Determine the active tab's probe data for chart rendering
  const activeProbeTab = sidebarTabs.find(t => t.id === activeTab);
  const activeProbeReading = activeProbeTab
    ? summary.readings.find(r => {
        if (dataSource === 'fusion') return r.did === activeProbeTab.did;
        return r.probe_name === activeProbeTab.probeName;
      })
    : null;
  const activeProbeDataKey = activeProbeReading ? getProbeDataKey(activeProbeReading) : '';
  const activeChartData = activeProbeDataKey ? probeData[activeProbeDataKey] : [];

  return (
    <div className="min-h-screen bg-slate-900 flex">
      {/* Sidebar */}
      <nav className="w-56 bg-slate-800 p-4 flex flex-col">
        <h2 className="text-teal-400 font-bold text-lg mb-6">ReefMind</h2>

        {sidebarTabs.map(tab => (
          <button key={tab.id} onClick={() => setActiveTab(tab.id)}
            className={`text-left px-3 py-2 rounded mb-1 ${
              activeTab === tab.id
                ? 'bg-teal-600 text-white'
                : 'text-slate-300 hover:bg-slate-700'
            }`}>
            {tab.icon} {tab.label}
          </button>
        ))}

        <div className="flex-1" />
        {dataSource === 'fusion' && (
          <div className="bg-green-900/30 text-green-300 rounded px-3 py-1 mb-2 text-xs text-center">
            ✅ Live from Fusion
          </div>
        )}
        {dataSource === 'agent' && (
          <div className="bg-blue-900/30 text-blue-300 rounded px-3 py-1 mb-2 text-xs text-center">
            📡 Agent data
          </div>
        )}
        <a href="/settings" className="text-slate-400 hover:text-white px-3 py-2 text-sm">⚙️ Settings</a>
        <a href="/csv-import" className="text-slate-400 hover:text-white px-3 py-2 text-sm">📁 CSV Import</a>
        <button onClick={() => { localStorage.clear(); window.location.href = '/login'; }}
          className="text-slate-400 hover:text-red-400 px-3 py-2 text-sm text-left">🚪 Sign Out</button>
      </nav>

      {/* Main */}
      <div className="flex-1 p-6 overflow-auto">
        {/* Duration selector — only show when there's data to chart */}
        {hasData && activeTab !== 'overview' && activeTab !== 'outlets' && (
          <div className="flex gap-2 mb-4">
            {['1h', '6h', '24h'].map(d => (
              <button key={d} onClick={() => setDuration(d)}
                className={`px-3 py-1 rounded text-sm ${duration === d ? 'bg-teal-600 text-white' : 'bg-slate-700 text-slate-300 hover:bg-slate-600'}`}>
                {d}
              </button>
            ))}
          </div>
        )}

        {loading ? (
          <div className="text-slate-400 text-center py-20">Loading dashboard...</div>

        ) : !hasData ? (
          <div className="text-center py-16">
            <div className="text-6xl mb-6">🐠</div>
            <h2 className="text-2xl font-bold text-white mb-3">Welcome to ReefMind!</h2>
            <p className="text-slate-400 max-w-md mx-auto mb-8">
              Connect Apex Fusion to see your live tank data instantly.
            </p>
            <div className="max-w-sm mx-auto space-y-4 text-left">
              <div className="bg-slate-800 rounded-lg p-4">
                <h3 className="text-teal-400 font-semibold mb-2">🔗 Connect Apex Fusion</h3>
                <p className="text-slate-400 text-sm">
                  Go to <a href="/settings" className="text-teal-400 hover:underline">Settings</a> and enter your Fusion credentials.
                </p>
              </div>
              <div className="bg-slate-800 rounded-lg p-4">
                <h3 className="text-teal-400 font-semibold mb-2">🔍 Auto-Discovery</h3>
                <p className="text-slate-400 text-sm">
                  Click "Discover My Tank" then "Save & Activate Dashboard".
                </p>
              </div>
            </div>
          </div>

        ) : activeTab === 'overview' ? (
          <>
            {/* Live reading cards — one per active probe */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
              {summary.readings.map(r => valueCard(r))}
            </div>

            {/* Overview charts — top 4 probes */}
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

              {/* Outlet grid */}
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
          /* Probe detail chart */
          <TimeSeriesChart title={activeProbeTab.label}
            data={activeChartData}
            yLabel={activeProbeReading?.unit || ''}
            color={getMeta(activeProbeReading?.probe_type || '').chartColor}
            large />

        ) : activeProbeTab && activeChartData.length === 0 ? (
          /* Probe selected but no chart data yet */
          <div className="text-slate-400 text-center py-20">
            <div className="text-4xl mb-4">{activeProbeTab.icon}</div>
            <p className="text-lg text-slate-300 mb-2">{activeProbeTab.label}</p>
            <p className="text-sm">Loading chart data...</p>
          </div>

        ) : null}
      </div>

      {/* Nemo chat */}
      <NemoWidget />
    </div>
  );
}
