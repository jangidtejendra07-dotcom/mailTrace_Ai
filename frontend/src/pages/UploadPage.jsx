import { useState, useCallback, useRef } from 'react'
import { UploadCloud, Loader2, FileWarning, ChevronRight } from 'lucide-react'
import { analyzeEmail } from '../lib/api.js'
import ResultPanel from '../components/ResultPanel.jsx'

export default function UploadPage() {
  const [dragOver, setDragOver] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [result, setResult] = useState(null)
  const [fileName, setFileName] = useState(null)
  const inputRef = useRef(null)

  const handleFile = useCallback(async (file) => {
    if (!file) return
    setFileName(file.name)
    setError(null)
    setResult(null)
    setLoading(true)
    try {
      const data = await analyzeEmail(file)
      setResult(data)
    } catch (e) {
      setError(e?.response?.data?.detail || 'Analysis failed. Is the backend running on :8000?')
    } finally {
      setLoading(false)
    }
  }, [])

  return (
    <div className="max-w-7xl mx-auto px-8 py-10">
      <header className="mb-8">
        <p className="text-[11px] font-mono uppercase tracking-widest text-trace mb-1.5">SIH 26106 · Prototype Console</p>
        <h1 className="font-display text-3xl font-semibold text-slate-50 tracking-tight">Email Threat Detection &amp; Forensic Intelligence</h1>
        <p className="text-slate-400 text-sm mt-2 max-w-2xl">
          Upload a raw <span className="font-mono text-slate-300">.eml</span> file. MailTrace runs it through the AI intent
          engine, header/authentication forensics, attachment scanning and URL intelligence, then fuses the signals
          into one explainable decision — ALLOW, QUARANTINE, or BLOCK.
        </p>
      </header>

      {!result && (
        <div
          onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
          onDragLeave={() => setDragOver(false)}
          onDrop={(e) => {
            e.preventDefault()
            setDragOver(false)
            handleFile(e.dataTransfer.files?.[0])
          }}
          onClick={() => inputRef.current?.click()}
          className={`relative overflow-hidden rounded-2xl border-2 border-dashed cursor-pointer transition-colors
            flex flex-col items-center justify-center text-center py-20 px-6
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
              <Loader2 className="animate-spin text-trace mb-4" size={36} />
              <p className="font-mono text-sm text-slate-300">Running analysis pipeline on {fileName}…</p>
              <p className="text-xs text-slate-500 mt-1">AI · Forensics · Attachment · URL Intel · Risk Fusion</p>
            </>
          ) : (
            <>
              <UploadCloud className="text-trace mb-4" size={36} strokeWidth={1.6} />
              <p className="font-medium text-slate-200">Drop a .eml file here, or click to browse</p>
              <p className="text-xs text-slate-500 mt-1.5 font-mono">POST /api/v1/analyze-email</p>
            </>
          )}
        </div>
      )}

      {error && (
        <div className="mt-4 rounded-lg border border-signal-danger/40 bg-signal-danger/10 px-4 py-3 flex items-center gap-2 text-sm text-signal-danger">
          <FileWarning size={16} /> {error}
        </div>
      )}

      {result && (
        <>
          <div className="flex items-center justify-between mb-5">
            <p className="text-sm text-slate-400 font-mono">Analyzed: <span className="text-slate-200">{fileName}</span></p>
            <button
              onClick={() => { setResult(null); setFileName(null); setError(null) }}
              className="inline-flex items-center gap-1 text-xs font-mono text-trace hover:text-trace/80"
            >
              Analyze another email <ChevronRight size={14} />
            </button>
          </div>
          <ResultPanel result={result} />
        </>
      )}
    </div>
  )
}
