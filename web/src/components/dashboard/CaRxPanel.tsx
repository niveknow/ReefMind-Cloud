import React from 'react';

interface CaRxPanelProps {
  effluentPH: number;
  alkalinity: number;
  co2Pressure: number;
  bubbleCount: number;
  status: 'active' | 'idle' | 'alarm';
}

export const CaRxPanel: React.FC<CaRxPanelProps> = ({ effluentPH, alkalinity, co2Pressure, bubbleCount, status }) => {
  const statusConfig = {
    active: { label: 'Active', color: 'bg-green-500' },
    idle: { label: 'Idle', color: 'bg-yellow-500' },
    alarm: { label: 'Alarm', color: 'bg-red-500' },
  };

  return (
    <div className="bg-slate-900/50 backdrop-blur-md border border-slate-700/50 p-4 rounded-xl shadow-lg">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-lg font-semibold text-slate-200">Calcium Reactor</h3>
        <span className={`px-2 py-1 rounded-full text-xs font-medium text-white flex items-center gap-1 ${statusConfig[status].color}`}>
          <span className="w-2 h-2 rounded-full bg-white animate-pulse" />
          {statusConfig[status].label}
        </span>
      </div>
      <div className="grid grid-cols-2 gap-4">
        <MetricCard label="Effluent pH" value={effluentPH.toFixed(2)} color="text-blue-400" />
        <MetricCard label="Alkalinity (dKH)" value={alkalinity.toFixed(1)} color="text-teal-400" />
        <MetricCard label="CO₂ (psi)" value={co2Pressure.toString()} color="text-amber-400" />
        <MetricCard label="Bubbles/min" value={bubbleCount.toString()} color="text-purple-400" />
      </div>
      <div className="mt-4 p-2 bg-slate-800/50 rounded-lg text-center text-xs text-slate-400">
        Normal Operation
      </div>
    </div>
  );
};

const MetricCard = ({ label, value, color }: { label: string; value: string; color: string }) => (
  <div className="bg-slate-950/50 p-3 rounded-lg border border-slate-800">
    <div className={`text-2xl font-bold ${color}`}>{value}</div>
    <div className="text-xs text-slate-400">{label}</div>
  </div>
);
