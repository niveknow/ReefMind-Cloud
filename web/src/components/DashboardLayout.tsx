import { ReactNode } from 'react';

interface Props {
  children: ReactNode;
}

export default function DashboardLayout({ children }: Props) {
  return (
    <div className="min-h-screen bg-slate-900 flex">
      {/* Sidebar */}
      <nav className="w-56 bg-slate-800 p-4 flex flex-col shrink-0">
        <a href="/dashboard" className="text-teal-400 font-bold text-lg mb-6 block">🏠 ReefMind</a>

        <a href="/dashboard" className="text-left px-3 py-2 rounded mb-1 text-slate-300 hover:bg-slate-700 block">
          📊 Dashboard
        </a>
        <a href="/water-tests" className="text-left px-3 py-2 rounded mb-1 bg-teal-600 text-white block">
          🧪 Water Tests
        </a>
        <a href="/notes" className="text-left px-3 py-2 rounded mb-1 text-slate-300 hover:bg-slate-700 block">
          📝 Notes
        </a>

        <div className="flex-1" />

        <a href="/settings" className="text-slate-400 hover:text-white px-3 py-2 text-sm block">⚙️ Settings</a>
        <a href="/csv-import" className="text-slate-400 hover:text-white px-3 py-2 text-sm block">📁 CSV Import</a>
        <button onClick={() => { localStorage.clear(); window.location.href = '/login'; }}
          className="text-slate-400 hover:text-red-400 px-3 py-2 text-sm text-left w-full">🚪 Sign Out</button>
      </nav>

      {/* Main */}
      <div className="flex-1 overflow-auto">
        {children}
      </div>
    </div>
  );
}
