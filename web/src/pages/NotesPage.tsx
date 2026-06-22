import React, { useEffect, useState } from 'react';
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

const NotesPage: React.FC = () => {
  const [notes, setNotes] = useState<TankNote[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

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

  return (
    <DashboardLayout>
      <div className="p-6">
        <h1 className="text-2xl font-bold mb-6">Tank Notes</h1>

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

        {!loading && !error && notes.length === 0 && (
          <div className="bg-gray-800/50 border border-gray-700 text-gray-400 p-8 rounded-lg text-center">
            <p className="text-lg mb-2">No tank notes available</p>
            <p className="text-sm">Notes will appear after the background collector syncs from Fusion (up to 6 hours).</p>
            <p className="text-sm mt-2">Make sure Fusion credentials are configured in Settings.</p>
          </div>
        )}

        {notes.map((note, idx) => {
          const style = NOTE_TYPE_STYLES[note.type_code] || NOTE_TYPE_STYLES['0'];
          return (
            <div
              key={note.note_id || idx}
              className="bg-gray-800/40 border border-gray-700 rounded-lg p-4 mb-3"
            >
              <div className="flex items-start justify-between mb-2">
                <div className="flex items-center gap-2">
                  <span
                    className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${style.bg} ${style.text}`}
                  >
                    {style.label}
                  </span>
                  <span className="text-gray-300 font-medium">
                    {note.title || 'Untitled'}
                  </span>
                </div>
                <span className="text-xs text-gray-500">{formatDate(note.time)}</span>
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
    </DashboardLayout>
  );
};

export default NotesPage;
