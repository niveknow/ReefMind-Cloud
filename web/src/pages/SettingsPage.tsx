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
  software: string;
  probes: { did: string; name: string; type: string; unit: string; value?: number }[];
  outlets: { did: string; name: string; type: string; state: string }[];
}

interface DiscoverResult {
  controllers: DiscoveredController[];
  account: { username: string; email: string };
}

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
  // Nemo settings
  const [nemoApiKey, setNemoApiKey] = useState('');
  const [nemoProvider, setNemoProvider] = useState('deepseek');
  const [nemoModel, setNemoModel] = useState('deepseek-chat');
  const [savingNemo, setSavingNemo] = useState(false);
  const [nemoSaved, setNemoSaved] = useState(false);

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

        {/* Navigation */}
        <div className="flex gap-4">
          <a href="/dashboard" className="text-teal-400 hover:underline text-sm">← Back to Dashboard</a>
          <a href="/csv-import" className="text-teal-400 hover:underline text-sm">📁 CSV Import →</a>
        </div>
      </div>
    </div>
  );
}
