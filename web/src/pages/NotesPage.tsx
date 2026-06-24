import React, { useEffect, useState, useMemo } from 'react';
import DashboardLayout from '../components/layout/DashboardLayout';

interface TankNote {
  note_id: string;
  type_code: string;
  type_name: string;
  title: string;
  reason_code: string;
  has_comment: boolean;
  comment: string;
  time: string;
}

interface NotesResponse {
  notes: TankNote[];
}

const NOTE_TYPE_STYLES: Record<string, { bg: string; text: string; label: string }> = {
  '0': { bg: 'bg-gray-600', text: 'text-white', label: 'Basic' },
  '1': { bg: 'bg-green-600', text: 'text-white', label: 'Good' },
  '2': { bg: 'bg-red-600', text: 'text-white', label: 'Bad' },
  '3': { bg: 'bg-gray-800', text: 'text-gray-200', label: 'Ugly' },
  '4': { bg: 'bg-blue-600', text: 'text-white', label: 'Maintenance' },
  '5': { bg: 'bg-purple-600', text: 'text-white', label: 'Event' },
};

type FilterPreset = 'all' | '1y' | '6m' | '3m' | '1m' | '1w';

const FILTER_PRESETS: { key: FilterPreset; label: string; days: number | null }[] = [
  { key: 'all', label: 'All Time', days: null },
  { key: '1y', label: '1 Year', days: 365 },
  { key: '6m', label: '6 Months', days: 180 },
  { key: '3m', label: '3 Months', days: 90 },
  { key: '1m', label: 'This Month', days: 30 },
  { key: '1w', label: 'This Week', days: 7 },
];

const NotesPage: React.FC = () => {
  const [notes, setNotes] = useState<TankNote[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<FilterPreset>('all');
  const [selectedMonth, setSelectedMonth] = useState<string>('');

  useEffect(() => {
    const token = localStorage.getItem('reefmind_token');
    if (!token) return;

    fetch('/api/telemetry/notes', {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then((json: NotesResponse) => {
        const sorted = (json.notes || []).sort(
          (a, b) => new Date(b.time).getTime() - new Date(a.time).getTime()
        );
        setNotes(sorted);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  }, []);

  // Derive available months from data
  const availableMonths = useMemo(() => {
    const months = new Set<string>();
    for (const n of notes) {
      try {
        const d = new Date(n.time);
        months.add(`${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`);
      } catch { /* skip */ }
    }
    return Array.from(months).sort().reverse();
  }, [notes]);

  // Filter notes by selected preset or month
  const filteredNotes = useMemo(() => {
    let filtered = notes;

    // Month override takes priority if set
    if (selectedMonth) {
      filtered = filtered.filter((n) => {
        try {
          const d = new Date(n.time);
          const key = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
          return key === selectedMonth;
        } catch {
          return false;
        }
      });
    } else {
      const preset = FILTER_PRESETS.find((p) => p.key === filter);
      if (preset && preset.days !== null) {
        const cutoff = Date.now() - preset.days * 24 * 60 * 60 * 1000;
        filtered = filtered.filter((n) => {
          try {
            return new Date(n.time).getTime() >= cutoff;
          } catch {
            return false;
          }
        });
      }
    }

    return filtered;
  }, [notes, filter, selectedMonth]);

  // Group notes by month for display
  const groupedNotes = useMemo(() => {
    const groups: Record<string, TankNote[]> = {};
    for (const n of filteredNotes) {
      try {
        const d = new Date(n.time);
        const key = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
        if (!groups[key]) groups[key] = [];
        groups[key].push(n);
      } catch {
        if (!groups['_other']) groups['_other'] = [];
        groups['_other'].push(n);
      }
    }
    return Object.entries(groups)
      .filter(([k]) => k !== '_other')
      .sort(([a], [b]) => b.localeCompare(a));
  }, [filteredNotes]);

  const formatDate = (dateStr: string) => {
    try {
      return new Date(dateStr).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return dateStr;
    }
  };

  const formatMonthLabel = (key: string) => {
    const [y, m] = key.split('-');
    const d = new Date(parseInt(y), parseInt(m) - 1);
    return d.toLocaleDateString('en-US', { year: 'numeric', month: 'long' });
  };

  const handleFilterClick = (key: FilterPreset) => {
    setFilter(key);
    setSelectedMonth('');
  };

  const handleMonthClick = (month: string) => {
    setSelectedMonth(month === selectedMonth ? '' : month);
    setFilter('all');
  };

  return (
    <DashboardLayout>
      <div className="p-6">
        <h1 className="text-2xl font-bold mb-4">Tank Notes</h1>

        {/* Filter bar */}
        <div className="flex flex-wrap items-center gap-2 mb-4">
          {/* Time range presets */}
          <div className="flex flex-wrap gap-1.5">
            {FILTER_PRESETS.map((p) => (
              <button
                key={p.key}
                onClick={() => handleFilterClick(p.key)}
                className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
                  filter === p.key && !selectedMonth
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-700/50 text-gray-300 hover:bg-gray-600/50'
                }`}
              >
                {p.label}
              </button>
            ))}
          </div>

          {/* Divider */}
          <span className="text-gray-600 text-xs mx-1">|</span>

          {/* Month picker */}
          <div className="relative">
            <select
              value={selectedMonth}
              onChange={(e) => handleMonthClick(e.target.value)}
              className={`px-3 py-1.5 text-xs font-medium rounded-md appearance-none cursor-pointer ${
                selectedMonth
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-700/50 text-gray-300 hover:bg-gray-600/50'
              }`}
            >
              <option value="" className="bg-gray-800 text-gray-300">
                Jump to month...
              </option>
              {availableMonths.map((m) => (
                <option key={m} value={m} className="bg-gray-800 text-gray-300">
                  {formatMonthLabel(m)}
                </option>
              ))}
            </select>
          </div>

          {/* Note count badge */}
          <span className="text-xs text-gray-500 ml-auto">
            {filteredNotes.length} of {notes.length} notes
          </span>
        </div>

        {loading && (
          <div className="flex items-center justify-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
            <span className="ml-3 text-gray-400">Loading notes...</span>
          </div>
        )}

        {error && (
          <div className="bg-red-900/20 border border-red-800 text-red-300 p-4 rounded-lg mb-4">
            Error: {error}
          </div>
        )}

        {!loading && !error && filteredNotes.length === 0 && (
          <div className="bg-gray-800/50 border border-gray-700 text-gray-400 p-8 rounded-lg text-center">
            <p className="text-lg mb-2">No tank notes match this filter</p>
            <p className="text-sm">
              <button onClick={() => { setFilter('all'); setSelectedMonth(''); }} className="text-blue-400 hover:underline">
                Clear filter
              </button>
              {' '}to show all notes.
            </p>
          </div>
        )}

        {!loading && !error && groupedNotes.map(([monthKey, monthNotes]) => (
          <div key={monthKey} className="mb-6">
            <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-3 border-b border-gray-700 pb-2">
              {formatMonthLabel(monthKey)}
              <span className="text-gray-600 font-normal ml-2">({monthNotes.length})</span>
            </h2>

            {monthNotes.map((note, idx) => {
              const style = NOTE_TYPE_STYLES[note.type_code] || NOTE_TYPE_STYLES['0'];
              return (
                <div
                  key={note.note_id || `${monthKey}-${idx}`}
                  className="bg-gray-800/40 border border-gray-700 rounded-lg p-4 mb-3"
                >
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <span
                        className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${style.bg} ${style.text}`}
                      >
                        {style.label}
                      </span>
                      <span className="text-gray-300 font-medium truncate max-w-md">
                        {note.title || 'Untitled'}
                      </span>
                    </div>
                    <span className="text-xs text-gray-500 whitespace-nowrap ml-2">
                      {formatDate(note.time)}
                    </span>
                  </div>
                  {note.comment && (
                    <p className="text-gray-400 text-sm mt-1 whitespace-pre-wrap">
                      {note.comment}
                    </p>
                  )}
                  {note.reason_code && note.reason_code !== '0' && (
                    <div className="text-xs text-gray-500 mt-1">
                      Reason code: {note.reason_code}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        ))}
      </div>
    </DashboardLayout>
  );
};

export default NotesPage;
