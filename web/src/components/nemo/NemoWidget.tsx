import { useState, useEffect } from 'react';
import api from '../../api/client';

export default function NemoWidget() {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<{ role: string; content: string }[]>([]);
  const [question, setQuestion] = useState('');
  const [loading, setLoading] = useState(false);
  const [configured, setConfigured] = useState<boolean | null>(null);

  useEffect(() => {
    if (open && configured === null) {
      api.get('/api/nemo/status')
        .then(res => setConfigured(res.data?.configured || false))
        .catch(() => setConfigured(false));
    }
  }, [open]);

  const ask = async () => {
    if (!question.trim() || loading) return;

    const userMsg = { role: 'user', content: question };
    setMessages(prev => [...prev, userMsg]);
    setQuestion('');
    setLoading(true);

    try {
      const res = await api.post('/api/nemo/ask', { question: userMsg.content });
      setMessages(prev => [...prev, { role: 'assistant', content: res.data.answer }]);
    } catch (err: any) {
      const detail = err.response?.data?.detail || 'Failed to reach Nemo';
      setMessages(prev => [...prev, { role: 'assistant', content: `❌ ${detail}` }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      {/* FAB */}
      <button onClick={() => setOpen(!open)}
        className="fixed bottom-6 right-6 w-14 h-14 bg-teal-600 hover:bg-teal-500 text-white rounded-full shadow-lg flex items-center justify-center text-2xl z-50 transition">
        {open ? '✕' : '🐟'}
      </button>

      {/* Chat panel */}
      {open && (
        <div className="fixed bottom-24 right-6 w-80 md:w-96 bg-slate-800 rounded-xl shadow-2xl border border-slate-700 z-50 flex flex-col"
          style={{ maxHeight: '60vh' }}>

          {/* Header */}
          <div className="bg-teal-600 text-white rounded-t-xl px-4 py-3 font-semibold flex items-center gap-2">
            🐟 Nemo
            {configured === false && (
              <span className="text-xs bg-slate-800/50 px-2 py-0.5 rounded">⚠️ Not configured</span>
            )}
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-3 space-y-2" style={{ minHeight: '200px' }}>
            {messages.length === 0 && (
              <div className="text-slate-500 text-sm text-center py-8">
                {configured === null ? (
                  <p>Checking configuration...</p>
                ) : configured ? (
                  <div>
                    <p className="text-slate-400 mb-2">Ask me anything about reef keeping!</p>
                    <p className="text-xs text-slate-500">e.g. "What's a good alkalinity level?"</p>
                  </div>
                ) : (
                  <div>
                    <p className="text-slate-400 mb-2">Nemo AI is not configured yet.</p>
                    <p className="text-xs text-slate-500">
                      Go to <a href="/settings" className="text-teal-400 hover:underline">Settings → AI Assistant</a> to add your API key.
                    </p>
                  </div>
                )}
              </div>
            )}
            {messages.map((m, i) => (
              <div key={i} className={`${m.role === 'user' ? 'text-right' : ''}`}>
                <span className={`inline-block px-3 py-2 rounded-lg text-sm max-w-xs ${
                  m.role === 'user'
                    ? 'bg-teal-600 text-white'
                    : 'bg-slate-700 text-slate-200'
                }`}>
                  {m.content}
                </span>
              </div>
            ))}
            {loading && (
              <div className="text-left">
                <span className="inline-block px-3 py-2 rounded-lg text-sm bg-slate-700 text-slate-400">
                  <span className="animate-pulse">Thinking...</span>
                </span>
              </div>
            )}
          </div>

          {/* Input */}
          {configured && (
            <div className="p-3 border-t border-slate-700 flex gap-2">
              <input
                value={question}
                onChange={e => setQuestion(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && ask()}
                placeholder="Ask Nemo..."
                className="flex-1 bg-slate-700 text-white rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500"
              />
              <button onClick={ask} disabled={loading}
                className="bg-teal-600 hover:bg-teal-500 text-white px-3 py-2 rounded-lg text-sm disabled:opacity-50">
                Send
              </button>
            </div>
          )}
        </div>
      )}
    </>
  );
}
