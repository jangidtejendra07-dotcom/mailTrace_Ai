import { useState, useCallback, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { X, UploadCloud, Loader2, FileWarning } from 'lucide-react'
import { analyzeEmail } from '../lib/api.js'

export default function UploadModal({ onClose }) {
  const navigate = useNavigate()
  const [dragOver, setDragOver] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [fileName, setFileName] = useState(null)
  const inputRef = useRef(null)

  const handleFile = useCallback(
    async (file) => {
      if (!file) return
      setFileName(file.name)
      setError(null)
      setLoading(true)
      try {
        const data = await analyzeEmail(file)
        navigate(`/cases/${data.case_id}`)
      } catch (e) {
        setError(e?.response?.data?.detail || 'Analysis failed. Please try again.')
      } finally {
        setLoading(false)
      }
    },
    [navigate]
  )

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-base-950/80 backdrop-blur-sm px-4">
      <div className="w-full max-w-lg rounded-2xl border border-base-700 bg-base-900 shadow-2xl">
        <div className="flex items-center justify-between px-5 py-4 border-b border-base-700">
          <h2 className="font-display text-lg font-semibold text-slate-100">Analyze an email</h2>
          <button onClick={onClose} className="text-slate-500 hover:text-slate-300 transition-colors" disabled={loading}>
            <X size={18} />
          </button>
        </div>

        <div className="p-5">
          <p className="text-sm text-slate-400 mb-4">
            Upload a raw <span className="font-mono text-slate-300">.eml</span> file. MailTrace runs it through the full
            detection pipeline — AI intent, forensics, attachments, URL intelligence — and creates a case.
          </p>

          <div
            onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
            onDragLeave={() => setDragOver(false)}
            onDrop={(e) => { e.preventDefault(); setDragOver(false); handleFile(e.dataTransfer.files?.[0]) }}
            onClick={() => !loading && inputRef.current?.click()}
            className={`relative overflow-hidden rounded-xl border-2 border-dashed cursor-pointer transition-colors
              flex flex-col items-center justify-center text-center py-14 px-6
              ${dragOver ? 'border-trace bg-trace/5' : 'border-base-600 hover:border-base-500 bg-base-900/40'}`}
          >
            {loading && (
              <div className="absolute inset-0 bg-gradient-to-b from-trace/10 to-transparent h-1/3 animate-scan pointer-events-none" />
            )}
            <input
              ref={inputRef}
              type="file"
              accept=".eml,.txt,.msg"
              className="hidden"
              onChange={(e) => handleFile(e.target.files?.[0])}
            />
            {loading ? (
              <>
                <Loader2 className="animate-spin text-trace mb-3" size={30} />
                <p className="font-mono text-sm text-slate-300">Analyzing {fileName}…</p>
                <p className="text-xs text-slate-500 mt-1">AI · Forensics · Attachment · URL Intel · Risk Fusion</p>
              </>
            ) : (
              <>
                <UploadCloud className="text-trace mb-3" size={30} strokeWidth={1.6} />
                <p className="font-medium text-slate-200 text-sm">Drop a .eml file here, or click to browse</p>
              </>
            )}
          </div>

          {error && (
            <div className="mt-4 rounded-lg border border-signal-danger/40 bg-signal-danger/10 px-4 py-2.5 flex items-center gap-2 text-sm text-signal-danger">
              <FileWarning size={16} /> {error}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
