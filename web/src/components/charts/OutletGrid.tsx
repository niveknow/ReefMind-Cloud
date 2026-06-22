import { useState, useEffect } from 'react';
import api from '../../api/client';

interface OutletState {
  outlet_name: string;
  state: number;
  state_display: string;
}

// Fusion outlet format from /api/fusion/outlets
interface FusionOutlet {
  did: string;
  name: string;
  type: string;
  state: string;
}

interface OutletGridProps {
  outlets?: FusionOutlet[];
}

export default function OutletGrid({ outlets: fusionOutlets }: OutletGridProps) {
  const [agentOutlets, setAgentOutlets] = useState<OutletState[]>([]);
  const [loadingOutlets, setLoadingOutlets] = useState(false);

  // Debug info
  const debugInfo = `OutletGrid: ${fusionOutlets ? fusionOutlets.length : 0} fusion, ${agentOutlets.length} agent, loading=${loadingOutlets}`;

  // Load outlets from API if parent didn't pass any
  useEffect(() => {
    if (!fusionOutlets || fusionOutlets.length === 0) {
      loadOutlets();
    }
  }, [fusionOutlets]);

  const loadOutlets = async () => {
    setLoadingOutlets(true);
    try {
      const res = await api.get('/api/telemetry/outlets');
      if (res.data?.outlets?.length > 0) {
        // Convert from API format to FusionOutlet format
        const mapped = res.data.outlets.map((o: any) => ({
          did: o.outlet_name,
          name: o.outlet_name,
          type: 'OUTLET',
          state: o.state_display,
        }));
        // Set as agent outlets to render in fallback
        setAgentOutlets(res.data.outlets);
        // Also expose as fusionOutlets by passing through parent won't update
        // We'll render agentOutlets directly below
        return;
      }
    } catch (e) {
      console.error('OutletGrid: failed to load outlets', e);
    } finally {
      setLoadingOutlets(false);
    }
  };

  // If fusion outlets provided, render them
  if (fusionOutlets && fusionOutlets.length > 0) {
    return (
      <div className="bg-slate-800 rounded-lg p-4">
        <div className="text-xs text-slate-500 mb-1">{debugInfo}</div>
        <h3 className="text-slate-200 font-semibold mb-3">🔌 Outlet States</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
          {fusionOutlets.map(o => {
            const isOn = o.state === 'ON' || o.state === 'PF1' || o.state === 'PF2' || o.state === 'PF3' || o.state === 'PF4';
            const colorClass = isOn ? 'bg-green-900/50 text-green-300' : 'bg-slate-700/50 text-slate-400';
            const stateIcon = isOn ? '●' : '○';
            const stateLabel = isOn ? 'ON' : o.state || 'OFF';
            return (
              <div key={o.did}
                className={`${colorClass} rounded px-3 py-2 text-sm font-medium`}>
                {o.name}
                <span className="ml-2">{stateIcon} {stateLabel}</span>
              </div>
            );
          })}
        </div>
      </div>
    );
  }

  // Fallback: no data from either source
  return (
    <div className="bg-slate-800 rounded-lg p-4">
      <div className="text-xs text-slate-500 mb-1">{debugInfo}</div>
      <h3 className="text-slate-200 font-semibold mb-3">🔌 Outlet States</h3>
      {agentOutlets.length === 0 ? (
        <p className="text-slate-500 text-sm">No outlet data available yet. Connect Fusion or deploy the agent to see outlet states.</p>
      ) : (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
          {agentOutlets.map(o => (
            <div key={o.outlet_name}
              className={`${o.state === 1 ? 'bg-green-900/50 text-green-300' : 'bg-slate-700/50 text-slate-400'} rounded px-3 py-2 text-sm font-medium`}>
              {o.outlet_name}
              <span className="ml-2">{o.state === 1 ? '● ON' : '○ OFF'}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
