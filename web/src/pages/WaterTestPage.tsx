import React, { useEffect, useState } from 'react';
import DashboardLayout from '../components/layout/DashboardLayout';
import TimeSeriesChart from '../components/charts/TimeSeriesChart';

interface WaterTest {
  time: string;
  parameter: string;
  value: number;
  unit: string;
}

interface WaterTestsResponse {
  water_tests: WaterTest[];
}

const WATER_TEST_COLORS: Record<string, string> = {
  'KH': '#3b82f6',
  'Ca': '#ef4444',
  'Mg': '#8b5cf6',
  'NO3': '#f59e0b',
  'PO4': '#10b981',
};

const WATER_TEST_RANGES: Record<string, { min: string; max: string }> = {
  'KH': { min: '7', max: '12' },
  'Ca': { min: '380', max: '450' },
  'Mg': { min: '1250', max: '1350' },
  'NO3': { min: '1', max: '10' },
  'PO4': { min: '0.01', max: '0.10' },
};

const WaterTestPage: React.FC = () => {
  const [data, setData] = useState<WaterTest[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const token = localStorage.getItem('reefmind_token');
    if (!token) return;

    fetch('/api/telemetry/water-tests', {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then((json: WaterTestsResponse) => {
        setData(json.water_tests || []);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  }, []);

  // Group by parameter
  const grouped = data.reduce<Record<string, WaterTest[]>>((acc, item) => {
    const param = item.parameter || 'Unknown';
    if (!acc[param]) acc[param] = [];
    acc[param].push(item);
    return acc;
  }, {});

  // Sort params: KH, Ca, Mg, NO3, PO4
  const paramOrder = ['KH', 'Ca', 'Mg', 'NO3', 'PO4'];
  const sortedParams = paramOrder.filter((p) => grouped[p]);

  return (
    <DashboardLayout>
      <div className="p-6">
        <h1 className="text-2xl font-bold mb-6">Water Tests</h1>

        {loading && (
          <div className="flex items-center justify-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
            <span className="ml-3 text-gray-400">Loading water tests...</span>
          </div>
        )}

        {error && (
          <div className="bg-red-900/20 border border-red-800 text-red-300 p-4 rounded-lg mb-4">
            Error: {error}
          </div>
        )}

        {!loading && !error && data.length === 0 && (
          <div className="bg-gray-800/50 border border-gray-700 text-gray-400 p-8 rounded-lg text-center">
            <p className="text-lg mb-2">No water test data available</p>
            <p className="text-sm">Data will appear after the background collector syncs from Fusion (up to 6 hours).</p>
            <p className="text-sm mt-2">Make sure Fusion credentials are configured in Settings.</p>
          </div>
        )}

        {sortedParams.map((param) => {
          const readings = grouped[param];
          const latest = readings[readings.length - 1];
          const color = WATER_TEST_COLORS[param] || '#6b7280';
          const range = WATER_TEST_RANGES[param];
          const unit = latest?.unit || '';

          return (
            <div key={param} className="bg-gray-800/40 border border-gray-700 rounded-lg p-4 mb-4">
              <div className="flex items-center justify-between mb-3">
                <h2 className="text-xl font-semibold" style={{ color }}>
                  {param}
                </h2>
                <div className="text-right">
                  <span className="text-3xl font-bold" style={{ color }}>
                    {latest ? latest.value : '--'}
                  </span>
                  <span className="text-gray-400 ml-1">{unit}</span>
                </div>
              </div>

              {range && (
                <div className="text-xs text-gray-500 mb-3">
                  Target: {range.min}–{range.max} {unit}
                </div>
              )}

              {/* Trend chart */}
              {readings.length > 1 && (
                <div className="mb-4">
                  <TimeSeriesChart
                    title=""
                    data={[...readings].sort((a, b) => new Date(a.time).getTime() - new Date(b.time).getTime())}
                    yLabel={unit}
                    color={color}
                    large={false}
                  />
                </div>
              )}

              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-gray-700 text-gray-400">
                      <th className="text-left py-2 pr-4">Date</th>
                      <th className="text-right py-2">Value</th>
                      <th className="text-right py-2 pl-4">Unit</th>
                    </tr>
                  </thead>
                  <tbody>
                    {[...readings].reverse().map((r, idx) => (
                      <tr key={idx} className="border-b border-gray-700/50">
                        <td className="py-2 pr-4 text-gray-300">
                          {new Date(r.time).toLocaleDateString('en-US', {
                            year: 'numeric',
                            month: 'short',
                            day: 'numeric',
                            hour: '2-digit',
                            minute: '2-digit',
                          })}
                        </td>
                        <td className="py-2 text-right font-mono">{r.value}</td>
                        <td className="py-2 pl-4 text-right text-gray-400">{r.unit}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          );
        })}
      </div>
    </DashboardLayout>
  );
};

export default WaterTestPage;
