import { useState, useRef } from 'react';
import api from '../api/client';

export default function CsvImportPage() {
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<any>(null);
  const [imports, setImports] = useState<any[]>([]);
  const [uploading, setUploading] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  const handleUpload = async () => {
    if (!file) return;
    setUploading(true);
    try {
      const formData = new FormData();
      formData.append('file', file);
      const res = await api.post('/api/csv/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      setPreview(res.data);
      loadImports();
    } catch (err) {
      console.error('Upload failed', err);
    } finally {
      setUploading(false);
    }
  };

  const loadImports = async () => {
    try {
      const res = await api.get('/api/csv/imports');
      setImports(res.data.imports || []);
    } catch {}
  };

  return (
    <div className="min-h-screen bg-slate-900 p-6">
      <div className="max-w-3xl mx-auto">
        <h1 className="text-2xl font-bold text-white mb-6">📁 CSV Import</h1>
        <p className="text-slate-400 mb-6">
          Import historical Apex data from a CSV export. The system will auto-detect columns and write to your time-series database.
        </p>

        <div className="bg-slate-800 rounded-lg p-6 mb-6">
          <div className="border-2 border-dashed border-slate-600 rounded-lg p-8 text-center"
            onDragOver={e => e.preventDefault()}
            onDrop={e => { e.preventDefault(); setFile(e.dataTransfer.files[0]); }}>
            <input ref={fileRef} type="file" accept=".csv" onChange={e => setFile(e.target.files?.[0] || null)}
              className="hidden" />
            {file ? (
              <div>
                <p className="text-teal-400 font-medium">{file.name}</p>
                <p className="text-slate-400 text-sm">{(file.size / 1024).toFixed(1)} KB</p>
                <div className="flex gap-2 justify-center mt-4">
                  <button onClick={() => { setFile(null); setPreview(null); }}
                    className="text-slate-400 hover:text-white text-sm">Change file</button>
                  <button onClick={handleUpload} disabled={uploading}
                    className="bg-teal-600 hover:bg-teal-500 text-white px-4 py-2 rounded text-sm disabled:opacity-50">
                    {uploading ? 'Uploading...' : 'Upload & Preview'}
                  </button>
                </div>
              </div>
            ) : (
              <div>
                <p className="text-slate-400 mb-2">Drop a CSV file here, or</p>
                <button onClick={() => fileRef.current?.click()}
                  className="bg-teal-600 hover:bg-teal-500 text-white px-4 py-2 rounded text-sm">
                  Browse Files
                </button>
              </div>
            )}
          </div>
        </div>

        {preview && (
          <div className="bg-slate-800 rounded-lg p-6 mb-6">
            <h2 className="text-lg font-semibold text-white mb-3">Preview: {preview.filename}</h2>
            <p className="text-slate-400 text-sm mb-3">{preview.file_size} bytes · {preview.headers?.length || 0} columns</p>
            {preview.headers && preview.headers.length > 0 && (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="bg-slate-700">
                      {preview.headers.map((h: string, i: number) => (
                        <th key={i} className="px-3 py-2 text-left text-slate-300 font-medium">{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {(preview.preview_rows || []).map((row: string[], ri: number) => (
                      <tr key={ri} className="border-t border-slate-700">
                        {row.map((cell: string, ci: number) => (
                          <td key={ci} className="px-3 py-2 text-slate-300">{cell}</td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            <p className="text-amber-400 text-sm mt-4">
                            Column mapping confirmation will be available in the next update.
                          </p>
          </div>
        )}

        <div className="bg-slate-800 rounded-lg p-6">
          <h2 className="text-lg font-semibold text-white mb-3">Import History</h2>
          {imports.length === 0 ? (
            <p className="text-slate-500 text-sm">No imports yet.</p>
          ) : (
            <div className="space-y-2">
              {imports.map((imp: any) => (
                <div key={imp.id} className="flex justify-between items-center bg-slate-700/50 rounded px-4 py-2">
                  <div>
                    <span className="text-slate-200 text-sm">{imp.filename}</span>
                    <span className="text-slate-400 text-xs ml-2">({imp.rows_imported} rows)</span>
                  </div>
                  <span className={`text-xs px-2 py-1 rounded ${imp.status === 'completed' ? 'bg-green-900 text-green-300' : imp.status === 'failed' ? 'bg-red-900 text-red-300' : 'bg-amber-900 text-amber-300'}`}>
                    {imp.status}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="mt-6">
          <a href="/dashboard" className="text-teal-400 hover:underline text-sm">← Back to Dashboard</a>
        </div>
      </div>
    </div>
  );
}
