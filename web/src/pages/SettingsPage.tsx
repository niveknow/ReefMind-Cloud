import { useState, useEffect } from 'react';
import api from '../api/client';

interface FusionStatus {
  connected: boolean;
  fusion_user: string;
  fusion_apex_id: string;
  has_creds: boolean;
  has_apex_id: boolean;
  discovered: boolean;
}

interface DiscoveredController {
  apex_id: string;
  name: string;
  type: string;
  serial: string;
  hardware: string;
  hardware_revision?: string;
  software: string;
  software_version?: string;
  timezone?: string;
  probes: { did: string; name: string; type: string; unit: string; value?: number }[];
  outlets: { did: string; name: string; type: string; state: string }[];
}

interface DiscoverResult {
  controllers: DiscoveredController[];
  account: { username: string; email: string };
}

const ALL_AREA_IDS = ['probes', 'outlets', 'water_tests', 'notes', 'power', 'trident'] as const;

const DATA_AREA_DEFS: Record<string, { icon: string; label: string; desc: string }> = {
  probes:      { icon: '🌡️', label: 'Probes',        desc: 'Live Temp, pH, ORP, Salinity readings every 5 min' },
  outlets:     { icon: '🔌', label: 'Outlets',       desc: 'ON/OFF/AON states for all named outlets' },
  water_tests: { icon: '🧪', label: 'Water Tests',   desc: 'Manual test results — KH, Ca, Mg, NO3, PO4' },
  notes:       { icon: '📝', label: 'Tank Notes',    desc: 'System notes, maintenance logs, and events' },
  power:       { icon: '⚡', label: 'Power Usage',   desc: 'Per-outlet wattage & amperage from EnergyBar 832/632' },
  trident:     { icon: '🤖', label: 'Trident',       desc: 'Auto alk/ca/mg readings (requires Trident hardware)' },
};

export default function SettingsPage() {
  const [fusionUser, setFusionUser] = useState('');
  const [fusionPass, setFusionPass] = useState('');
  const [config, setConfig] = useState<any>({});
  const [status, setStatus] = useState<FusionStatus | null>(null);
  const [discovering, setDiscovering] = useState(false);
  const [discoverResult, setDiscoverResult] = useState<DiscoverResult | null>(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [enabledAreas, setEnabledAreas] = useState<string[]>(['probes', 'outlets', 'water_tests', 'notes', 'power', 'trident']);
  // Nemo settings
  const [nemoApiKey, setNemoApiKey] = useState('');
  const [nemoProvider, setNemoProvider] = useState('deepseek');
  const [nemoModel, setNemoModel] = useState('deepseek-chat');
  const [savingNemo, setSavingNemo] = useState(false);
  const [nemoSaved, setNemoSaved] = useState(false);
  // Controller info from config_json
  const [controllers, setControllers] = useState<DiscoveredController[]>([]);
  // Backfill
  const [backfillDays, setBackfillDays] = useState(30);
  const [savingBackfill, setSavingBackfill] = useState(false);
  const [backfillSaved, setBackfillSaved] = useState(false);

  useEffect(() => {
    loadStatus();
    loadConfig();
  }, []);

  const loadStatus = async () => {
    try {
      const res = await api.get('/api/fusion/status');
      setStatus(res.data);
      if (res.data.fusion_user) setFusionUser(res.data.fusion_user);
    } catch { /* ignore */ }
  };

  const loadConfig = async () => {
    try {
      const res = await api.get('/api/tenant/config');
      const c = res.data.config || {};
      setConfig(c);
      if (c.nemo_provider) setNemoProvider(c.nemo_provider);
      if (c.nemo_model) setNemoModel(c.nemo_model);
      if (c.nemo_configured) {
        setNemoApiKey('********'); // masked — key never sent to frontend
      }
      // Parse controllers from config_json
      try {
        const parsed = JSON.parse(c.config_json || '{}');
        setControllers(parsed.controllers || []);
        setBackfillDays(parsed.backfill_days || 30);
      } catch {}
    } catch { /* ignore */ }
  };

  const handleDiscover = async () => {
    if (!fusionUser || !fusionPass) {
      setError('Please enter your Fusion username and password');
      return;
    }
    setDiscovering(true);
    setError('');
    setDiscoverResult(null);
    try {
      const res = await api.post('/api/fusion/discover', {
        fusion_username: fusionUser,
        fusion_password: fusionPass,
      });
      setDiscoverResult(res.data.discovered);
      setSuccess(`Found ${res.data.discovered.controllers.length} controller(s)!`);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to connect to Apex Fusion');
    } finally {
      setDiscovering(false);
    }
  };

  const handleSave = async () => {
    if (!discoverResult || !discoverResult.controllers.length) return;
    setSaving(true);
    try {
      await api.post('/api/fusion/save', {
        controller_id: discoverResult.controllers[0].apex_id,
        discovered_data: discoverResult,
        enabled_areas: enabledAreas,
      });
      setSaved(true);
      setSuccess('Configuration saved! Your dashboard is ready.');
      setTimeout(() => setSaved(false), 5000);
      loadStatus();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Save failed');
    } finally {
      setSaving(false);
    }
  };

  const copyApiKey = () => {
    if (config.agent_api_key) {
      navigator.clipboard.writeText(config.agent_api_key);
    }
  };

  const handleSaveNemo = async () => {
    if (!nemoApiKey.trim() || nemoApiKey === '********') {
      setError('Enter your AI API key');
      return;
    }
    setSavingNemo(true);
    setError('');
    try {
      await api.put('/api/tenant/config', {
        nemo_api_key: nemoApiKey,
        nemo_provider: nemoProvider,
        nemo_model: nemoModel,
      });
      setNemoSaved(true);
      setSuccess('AI Assistant configured! Nemo is ready.');
      setTimeout(() => setNemoSaved(false), 5000);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to save AI settings');
    } finally {
      setSavingNemo(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-900 p-6">
      <div className="max-w-2xl mx-auto">
        <h1 className="text-2xl font-bold text-white mb-6">⚙️ Settings</h1>

        {/* Agent API Key */}
        <div className="bg-slate-800 rounded-lg p-6 mb-6">
          <h2 className="text-lg font-semibold text-white mb-4">Agent API Key</h2>
          <p className="text-slate-400 text-sm mb-3">
            Use this key to authenticate your local ReefMind agent
          </p>
          <div className="flex gap-2 mb-3">
            <code className="flex-1 bg-slate-700 text-teal-300 rounded px-3 py-2 text-sm font-mono truncate">
              {config.agent_api_key || 'Register to get an API key'}
            </code>
            {config.agent_api_key && (
              <button onClick={copyApiKey} className="bg-slate-700 hover:bg-slate-600 text-white px-3 py-2 rounded text-sm">
                Copy
              </button>
            )}
          </div>
        </div>

        {/* Apex Fusion Connection */}
        <div className="bg-slate-800 rounded-lg p-6 mb-6">
          <h2 className="text-lg font-semibold text-white mb-2">🔗 Connect Apex Fusion</h2>
          <p className="text-slate-400 text-sm mb-4">
            Enter your Apex Fusion credentials to auto-discover your tank setup.
            We'll find your controller, probes, and outlets automatically.
          </p>

          {status?.connected && (
            <div className="bg-green-900/30 text-green-300 rounded px-4 py-2 mb-4 text-sm flex items-center gap-2">
              <span>✅</span> Connected as <strong>{status.fusion_user}</strong>
              {status.fusion_apex_id && <span className="text-xs opacity-70">(ID: {status.fusion_apex_id.slice(0, 8)}...)</span>}
            </div>
          )}

          <div className="mb-3">
            <label className="block text-slate-300 text-sm mb-1">Fusion Username (email)</label>
            <input
              type="email"
              value={fusionUser}
              onChange={e => setFusionUser(e.target.value)}
              className="w-full bg-slate-700 text-white rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-teal-500"
              placeholder="your@email.com"
            />
          </div>
          <div className="mb-4">
            <label className="block text-slate-300 text-sm mb-1">Fusion Password</label>
            <input
              type="password"
              value={fusionPass}
              onChange={e => setFusionPass(e.target.value)}
              className="w-full bg-slate-700 text-white rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-teal-500"
              placeholder="Your Fusion password"
            />
          </div>

          {error && (
            <div className="bg-red-900/50 text-red-300 px-4 py-2 rounded mb-4 text-sm">{error}</div>
          )}
          {success && (
            <div className="bg-green-900/50 text-green-300 px-4 py-2 rounded mb-4 text-sm">{success}</div>
          )}

          <button
            onClick={handleDiscover}
            disabled={discovering}
            className="bg-teal-600 hover:bg-teal-500 text-white font-semibold px-6 py-2 rounded disabled:opacity-50 transition"
          >
            {discovering ? (
              <span className="flex items-center gap-2">
                <span className="animate-pulse">🔍</span> Discovering...
              </span>
            ) : '🔍 Discover My Tank'}
          </button>

          {saved && (
            <span className="text-green-400 text-sm ml-3">✅ Saved!</span>
          )}
        </div>

        {/* Controller Info from config_json */}
        {controllers.length > 0 && (
          <div className="bg-slate-800 rounded-lg p-6 mb-6">
            <h2 className="text-lg font-semibold text-white mb-2">
              🖥️ Controllers ({controllers.length})
            </h2>
            <p className="text-slate-400 text-sm mb-4">
              Controllers discovered on your Apex Fusion account.
            </p>
            {controllers.map((ctrl, idx) => (
              <div key={idx} className="bg-slate-700/50 rounded-lg p-4 mb-3">
                <h3 className="text-teal-300 font-semibold text-base mb-2">
                  {ctrl.name}
                </h3>
                <div className="grid grid-cols-2 gap-2 text-sm">
                  <div>
                    <span className="text-xs text-slate-400 block">Model</span>
                    <span className="text-white font-mono text-xs">{ctrl.type || '—'}</span>
                  </div>
                  <div>
                    <span className="text-xs text-slate-400 block">Serial</span>
                    <span className="text-white font-mono text-xs">{ctrl.serial || '—'}</span>
                  </div>
                  <div>
                    <span className="text-xs text-slate-400 block">Hardware</span>
                    <span className="text-white font-mono text-xs">{ctrl.hardware_revision || ctrl.hardware || '—'}</span>
                  </div>
                  <div>
                    <span className="text-xs text-slate-400 block">Firmware</span>
                    <span className="text-white font-mono text-xs">{ctrl.software_version || ctrl.software || '—'}</span>
                  </div>
                  <div>
                    <span className="text-xs text-slate-400 block">Timezone</span>
                    <span className="text-white font-mono text-xs">{ctrl.timezone || '—'}</span>
                  </div>
                  <div>
                    <span className="text-xs text-slate-400 block">Apex ID</span>
                    <span className="text-white font-mono text-xs">{ctrl.apex_id || '—'}</span>
                  </div>
                  <div className="col-span-2">
                    <span className="text-xs text-slate-400 block">Probes</span>
                    <span className="text-white font-mono text-xs">{ctrl.probes?.length || 0}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {controllers.length === 0 && (
          <div className="bg-slate-800 rounded-lg p-6 mb-6">
            <h2 className="text-lg font-semibold text-white mb-2">🖥️ Controllers</h2>
            <p className="text-slate-400 text-sm">
              No controllers discovered yet. Use the <strong>Discover My Tank</strong> button above to find your Apex controllers.
            </p>
          </div>
        )}

        {/* Historical Data Backfill */}
        <div className="bg-slate-800 rounded-lg p-6 mb-6">
          <h2 className="text-lg font-semibold text-white mb-2">📊 Historical Data Backfill</h2>
          <p className="text-slate-400 text-sm mb-4">
            Backfill historical probe data when first connecting your tank.
            Changing this resets the backfill flag — data will re-sync on the next collection cycle.
          </p>
          <div className="flex items-center gap-3 mb-4">
            <select
              value={backfillDays}
              onChange={e => setBackfillDays(Number(e.target.value))}
              className="bg-slate-700 text-white rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500"
            >
              <option value={30}>30 Days</option>
              <option value={60}>60 Days</option>
              <option value={90}>90 Days</option>
            </select>
            <button
              onClick={async () => {
                setSavingBackfill(true);
                setError('');
                try {
                  await api.put('/api/tenant/config', { backfill_days: backfillDays });
                  setBackfillSaved(true);
                  setSuccess('Backfill settings saved! Data will re-sync on next collection.');
                  setTimeout(() => setBackfillSaved(false), 5000);
                } catch (err: any) {
                  setError(err.response?.data?.detail || 'Failed to save backfill settings');
                } finally {
                  setSavingBackfill(false);
                }
              }}
              disabled={savingBackfill}
              className="bg-teal-600 hover:bg-teal-500 text-white font-semibold px-4 py-2 rounded disabled:opacity-50 transition"
            >
              {savingBackfill ? 'Saving...' : 'Apply Backfill'}
            </button>
            {backfillSaved && <span className="text-green-400 text-sm">✅ Saved!</span>}
          </div>
          <div className="bg-amber-900/30 text-amber-300 rounded px-4 py-3 text-xs leading-relaxed">
            <strong>⚠️ API Note:</strong> Apex Fusion caps historical probe data at ~7 days.
            After the initial backfill, the system accumulates data via live 5-minute polling.
            The 30/60/90 day options set how much data eventually appears as the collector runs over time.
          </div>
        </div>

        {/* AI Assistant */}
        <div className="bg-slate-800 rounded-lg p-6 mb-6">
          <h2 className="text-lg font-semibold text-white mb-2">🐟 AI Assistant (Nemo)</h2>
          <p className="text-slate-400 text-sm mb-4">
            Optionally enter an AI API key to enable Nemo assistant in your dashboard.
            If left empty, Nemo stays in offline mode.
          </p>

          {config.nemo_configured && (
            <div className="bg-teal-900/30 text-teal-300 rounded px-4 py-2 mb-4 text-sm flex items-center gap-2">
              <span>✅</span> Nemo AI is active ({config.nemo_provider} / {config.nemo_model})
            </div>
          )}

          <div className="mb-3">
            <label className="block text-slate-300 text-sm mb-1">API Key</label>
            <input
              type="password"
              value={nemoApiKey}
              onChange={e => setNemoApiKey(e.target.value)}
              className="w-full bg-slate-700 text-white rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-teal-500 font-mono text-sm"
              placeholder="sk-... (DeepSeek, OpenAI, etc.)"
            />
            <p className="text-xs text-slate-500 mt-1">Your key is stored encrypted and never exposed to the browser.</p>
          </div>

          <div className="grid grid-cols-2 gap-3 mb-4">
            <div>
              <label className="block text-slate-300 text-sm mb-1">Provider</label>
              <select value={nemoProvider} onChange={e => setNemoProvider(e.target.value)}
                className="w-full bg-slate-700 text-white rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500">
                <option value="deepseek">DeepSeek</option>
                <option value="openai">OpenAI</option>
              </select>
            </div>
            <div>
              <label className="block text-slate-300 text-sm mb-1">Model</label>
              <input
                type="text"
                value={nemoModel}
                onChange={e => setNemoModel(e.target.value)}
                className="w-full bg-slate-700 text-white rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500"
                placeholder="deepseek-chat"
              />
            </div>
          </div>

          <button onClick={handleSaveNemo} disabled={savingNemo || !nemoApiKey.trim() || nemoApiKey === '********'}
            className="bg-teal-600 hover:bg-teal-500 text-white font-semibold px-6 py-2 rounded disabled:opacity-50 transition">
            {savingNemo ? 'Saving...' : '💾 Save AI Settings'}
          </button>
          {nemoSaved && <span className="text-green-400 text-sm ml-3">✅ Saved! Go try Nemo 🐟</span>}
        </div>

        {/* Discovery Results */}
        {discoverResult && discoverResult.controllers.length > 0 && (
          <div className="bg-slate-800 rounded-lg p-6 mb-6">
            <h2 className="text-lg font-semibold text-white mb-4">📡 Discovery Results</h2>

            {discoverResult.controllers.map((ctrl, idx) => (
              <div key={idx} className="bg-slate-700/50 rounded-lg p-4 mb-4">
                <h3 className="text-teal-300 font-semibold text-base">{ctrl.name}</h3>
                <p className="text-slate-400 text-xs mb-3 font-mono">ID: {ctrl.apex_id}</p>

                {/* Probes */}
                {ctrl.probes.length > 0 && (
                  <div className="mb-3">
                    <h4 className="text-slate-300 text-sm font-medium mb-2">Probes ({ctrl.probes.length})</h4>
                    <div className="grid grid-cols-2 gap-2">
                      {ctrl.probes.map((p, i) => (
                        <div key={i} className="bg-slate-800 rounded px-3 py-2 text-sm flex justify-between">
                          <span className="text-slate-200">{p.name}</span>
                          <span className="text-teal-400">{p.type} {p.unit}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* System info */}
                <div className="text-xs text-slate-400 space-y-1">
                  <p>🖥️ {ctrl.type} — {ctrl.serial}</p>
                  <p>📱 SW {ctrl.software} | HW {ctrl.hardware}</p>
                </div>
              </div>
            ))}

            {/* ── Select Data to Collect ── */}
            <div className="border-t border-slate-700/30 pt-4 mt-4 mb-4">
              <h3 className="text-sm font-semibold text-white mb-3">📡 Select Data to Collect</h3>
              <p className="text-xs text-slate-400 mb-3">
                All areas are enabled by default. Turn off anything that doesn't apply
                to your tank setup. You can change these later.
              </p>
              <div className="space-y-2">
                {ALL_AREA_IDS.map(aid => {
                  const def = DATA_AREA_DEFS[aid];
                  const on = enabledAreas.includes(aid);
                  return (
                    <label key={aid}
                      className="flex items-center gap-3 bg-slate-800/60 rounded-lg px-3 py-2.5 cursor-pointer hover:bg-slate-700/60 transition-colors">
                      <span className="text-base">{def.icon}</span>
                      <div className="flex-1 min-w-0">
                        <div className="text-sm font-medium text-white">{def.label}</div>
                        <div className="text-xs text-slate-400 truncate">{def.desc}</div>
                      </div>
                      <button type="button" role="switch" aria-checked={on}
                        onClick={() => {
                          setEnabledAreas(prev =>
                            on ? prev.filter(a => a !== aid) : [...prev, aid]
                          );
                        }}
                        className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors shrink-0 ${
                          on ? 'bg-teal-600' : 'bg-slate-600'
                        }`}>
                        <span className={`inline-block h-3.5 w-3.5 rounded-full bg-white transition-transform ${
                          on ? 'translate-x-[18px]' : 'translate-x-[2px]'
                        }`} />
                      </button>
                    </label>
                  );
                })}
              </div>
            </div>

            {!saved && (
              <button
                onClick={handleSave}
                disabled={saving}
                className="bg-green-600 hover:bg-green-500 text-white font-semibold px-6 py-2 rounded disabled:opacity-50 transition w-full"
              >
                {saving ? 'Saving...' : '✅ Save & Activate Dashboard'}
              </button>
            )}
          </div>
        )}

        {/* 📁 Import Dashboard */}
        <div className="bg-slate-800 rounded-lg p-6 mb-6">
          <h2 className="text-lg font-semibold text-white mb-2">📁 Import Dashboard</h2>
          <p className="text-slate-400 text-sm mb-4">
            Upload a dashboard definition JSON file to add custom layouts to your dashboard.
            Use the tab selector at the top of the dashboard to switch between layouts.
          </p>
          <div className="bg-slate-700/30 border border-dashed border-slate-600/50 rounded-lg p-6 text-center">
            <div className="text-3xl mb-2">📄</div>
            <p className="text-slate-400 text-sm mb-3">
              Upload a <code className="text-teal-300 bg-slate-700 px-1 rounded">.json</code> file with a <strong>DashboardDef</strong> schema
            </p>
            <label className="inline-block bg-teal-600 hover:bg-teal-500 text-white font-semibold px-6 py-2 rounded cursor-pointer transition disabled:opacity-50"
              id="dashboard-import-label">
              Choose File
              <input
                type="file"
                accept=".json"
                className="hidden"
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (!file) return;
                  const reader = new FileReader();
                  reader.onload = (ev) => {
                    try {
                      const def = JSON.parse(ev.target?.result as string);
                      if (!def.id || !def.name || !def.layout) {
                        setError('Invalid dashboard definition: missing id, name, or layout');
                        return;
                      }
                      // Save to localStorage
                      const raw = localStorage.getItem('reefmind_dashboards');
                      const layouts = raw ? JSON.parse(raw) : [];
                      const idx = layouts.findIndex((l: any) => l.id === def.id);
                      const entry = { id: def.id, name: def.name, def, importedAt: new Date().toISOString() };
                      if (idx >= 0) layouts[idx] = entry;
                      else layouts.push(entry);
                      localStorage.setItem('reefmind_dashboards', JSON.stringify(layouts));
                      setSuccess(`Dashboard "${def.name}" imported! Go to Dashboard to view it.`);
                    } catch {
                      setError('Failed to parse JSON file');
                    }
                  };
                  reader.readAsText(file);
                  e.target.value = '';
                }}
              />
            </label>
          </div>
          <div className="mt-3">
            <details className="text-xs text-slate-500">
              <summary className="cursor-pointer hover:text-slate-300">View JSON schema reference</summary>
              <pre className="mt-2 bg-slate-900 rounded p-3 text-slate-400 overflow-x-auto leading-relaxed">
{`{
  "id": "my-dash",
  "name": "My Dashboard",
  "description": "Optional description",
  "layout": [
    {
      "i": "widget-1",
      "type": "CaRxPanel",
      "x": 0, "y": 0, "w": 6, "h": 2
    },
    {
      "i": "chart-1",
      "type": "TimeSeriesChart",
      "x": 6, "y": 0, "w": 6, "h": 3,
      "props": { "id": "pH", "title": "pH", "color": "#a855f7" }
    },
    {
      "i": "probe-1",
      "type": "ProbeCard",
      "x": 0, "y": 2, "w": 3, "h": 1,
      "props": { "probeId": "Temp", "label": "Temp", "unit": "°F" }
    },
    {
      "i": "outlets-1",
      "type": "OutletGrid",
      "x": 0, "y": 3, "w": 12, "h": 3
    }
  ]
}

Widget types: CaRxPanel, TimeSeriesChart,
ProbeCard, OutletGrid, NemoWidget`}</pre>
            </details>
          </div>
        </div>

        {/* Navigation */}
        <div className="flex gap-4">
          <a href="/dashboard" className="text-teal-400 hover:underline text-sm">← Back to Dashboard</a>
          <a href="/csv-import" className="text-teal-400 hover:underline text-sm">📁 CSV Import →</a>
        </div>
      </div>
    </div>
  );
}
