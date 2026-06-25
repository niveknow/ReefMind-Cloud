import React from 'react';

interface ProbeCardProps {
  label: string;
  value: string;
  unit: string;
  icon?: React.ReactNode;
}

export const ProbeCard: React.FC<ProbeCardProps> = ({ label, value, unit, icon }) => {
  return (
    <div className="bg-slate-900/50 backdrop-blur-md border border-slate-700/50 p-4 rounded-xl flex flex-col justify-center items-center">
      <div className="text-slate-400 text-sm mb-1">{label}</div>
      <div className="text-2xl font-bold text-white">
        {value} <span className="text-sm font-normal text-slate-500">{unit}</span>
      </div>
    </div>
  );
};
