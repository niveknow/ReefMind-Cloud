import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import api from '../api/client';

export default function LoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const res = await api.post('/api/auth/login', { email, password });
      localStorage.setItem('reefmind_token', res.data.access_token);
      localStorage.setItem('reefmind_tenant_id', res.data.tenant_id);
      localStorage.setItem('reefmind_user_id', res.data.user_id);
      navigate('/dashboard');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-900 flex items-center justify-center px-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-teal-400">ReefMind</h1>
          <p className="text-slate-400 mt-2">Cloud Reef Aquarium Monitoring</p>
        </div>
        <form onSubmit={handleSubmit} className="bg-slate-800 rounded-lg p-8 shadow-xl">
          <h2 className="text-xl font-semibold text-white mb-6">Sign In</h2>
          {error && (
            <div className="bg-red-900/50 text-red-300 px-4 py-2 rounded mb-4 text-sm">{error}</div>
          )}
          <div className="mb-4">
            <label className="block text-slate-300 text-sm mb-1">Email</label>
            <input
              type="email" value={email} onChange={e => setEmail(e.target.value)}
              className="w-full bg-slate-700 text-white rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-teal-500"
              required
            />
          </div>
          <div className="mb-6">
            <label className="block text-slate-300 text-sm mb-1">Password</label>
            <input
              type="password" value={password} onChange={e => setPassword(e.target.value)}
              className="w-full bg-slate-700 text-white rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-teal-500"
              required
            />
          </div>
          <button
            type="submit" disabled={loading}
            className="w-full bg-teal-600 hover:bg-teal-500 text-white font-semibold py-2 rounded transition disabled:opacity-50"
          >
            {loading ? 'Signing in...' : 'Sign In'}
          </button>
          <p className="text-slate-400 text-sm text-center mt-4">
            Don't have an account? <Link to="/register" className="text-teal-400 hover:underline">Create one</Link>
          </p>
        </form>
      </div>
    </div>
  );
}
