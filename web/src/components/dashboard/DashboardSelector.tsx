import React from 'react';
import { DashboardDef } from '../../types/dashboard';

interface DashboardSelectorProps {
  dashboards: DashboardDef[];
  activeId: string;
  onSelect: (id: string) => void;
  onImport?: () => void;
  onDelete?: (id: string) => void;
}

export const DashboardSelector: React.FC<DashboardSelectorProps> = ({
  dashboards,
  activeId,
  onSelect,
  onImport,
  onDelete,
}) => {
  if (dashboards.length === 0) return null;

  return (
    <div className="mb-4">
      <div className="flex items-center gap-2 flex-wrap">
        {/* Default dashboard tab */}
        <button
          onClick={() => onSelect('__default__')}
          className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
            activeId === '__default__'
              ? 'bg-teal-600 text-white shadow-lg shadow-teal-600/20'
              : 'bg-slate-800 text-slate-300 hover:bg-slate-700 border border-slate-700/50'
          }`}
        >
          📊 Default
        </button>

        {/* Separator */}
        <span className="text-slate-600 text-sm mx-1">|</span>

        {/* Mock dashboards */}
        {dashboards.map(d => (
          <div key={d.id} className="relative group">
            <button
              onClick={() => onSelect(d.id)}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                activeId === d.id
                  ? 'bg-teal-600 text-white shadow-lg shadow-teal-600/20'
                  : 'bg-slate-800 text-slate-300 hover:bg-slate-700 border border-slate-700/50'
              }`}
              title={d.description}
            >
              {d.name}
            </button>
            {onDelete && activeId !== d.id && (
              <button
                onClick={(e) => { e.stopPropagation(); onDelete(d.id); }}
                className="absolute -top-1.5 -right-1.5 w-4 h-4 bg-red-500 rounded-full text-[10px] text-white opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center"
              >
                ×
              </button>
            )}
          </div>
        ))}

        {/* Import button */}
        {onImport && (
          <button
            onClick={onImport}
            className="px-3 py-2 rounded-lg text-sm font-medium text-slate-400 hover:text-white hover:bg-slate-800 border border-dashed border-slate-600/50 transition-all"
            title="Import a dashboard definition file"
          >
            + Import
          </button>
        )}
      </div>
    </div>
  );
};
