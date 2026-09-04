import { useEffect, useState, useCallback } from 'react'
import { Link } from 'react-router-dom'
import { FolderClock, ChevronRight, Loader2, Plus, Mail, UploadCloud } from 'lucide-react'
import { listCases } from '../lib/api.js'
import PageHeader from '../components/PageHeader.jsx'
import UploadModal from '../components/UploadModal.jsx'

const POLL_MS = 20000

const decisionStyle = {
  ALLOW: 'text-signal-safe bg-signal-safe/10 border-signal-safe/30',
  QUARANTINE: 'text-signal-watch bg-signal-watch/10 border-signal-watch/30',
  BLOCK: 'text-signal-critical bg-signal-critical/10 border-signal-critical/30',
}

const SOURCE_TABS = [
  { key: 'all', label: 'All' },
  { key: 'gmail', label: 'Gmail' },
  { key: 'upload', label: 'Uploaded' },
]

export default function CasesPage() {
  const [cases, setCases] = useState(null)
  const [error, setError] = useState(null)
  const [sourceFilter, setSourceFilter] = useState('all')
  const [decisionFilter, setDecisionFilter] = useState('all')
  const [uploadOpen, setUploadOpen] = useState(false)

  const load = useCallback(() => {
    listCases()
      .then((data) => { setCases(data); setError(null) })
      .catch(() => setError('Could not reach the MailTrace backend.'))
  }, [])

  useEffect(() => {
    load()
    const interval = setInterval(load, POLL_MS)
    return () => clearInterval(interval)
  }, [load])

  const filtered = (cases || []).filter((c) => {
    if (sourceFilter !== 'all' && c.source !== sourceFilter) return false
    if (decisionFilter !== 'all' && c.decision !== decisionFilter) return false
    return true
  })

  return (
    <div className="max-w-6xl mx-auto px-8 py-10">
      <PageHeader
        icon={FolderClock}
        title="Cases"
        subtitle="Every email MailTrace has analyzed — from manual uploads and your connected Gmail inbox — with evidence and forensic reports."
        right={
          <button
            onClick={() => setUploadOpen(true)}
            className="inline-flex items-center gap-2 rounded-lg bg-trace text-base-950 font-semibold text-sm px-4 py-2.5 hover:bg-trace/90 transition-colors shrink-0"
          >
            <Plus size={16} /> Analyze email
          </button>
        }
      />

      <div className="flex flex-wrap items-center justify-between gap-3 mb-5">
        <div className="flex items-center gap-1.5 rounded-lg border border-base-700 bg-base-900/60 p-1">
          {SOURCE_TABS.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setSourceFilter(tab.key)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
                sourceFilter === tab.key ? 'bg-trace/15 text-trace' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              {tab.key === 'gmail' && <Mail size={12} />}
              {tab.key === 'upload' && <UploadCloud size={12} />}
              {tab.label}
            </button>
          ))}
        </div>

        <select
          value={decisionFilter}
          onChange={(e) => setDecisionFilter(e.target.value)}
          className="bg-base-800 border border-base-600 rounded-lg px-3 py-1.5 text-xs text-slate-300 focus:outline-none focus:ring-2 focus:ring-trace/50"
        >
          <option value="all">All decisions</option>
          <option value="ALLOW">Allow</option>
          <option value="QUARANTINE">Quarantine</option>
          <option value="BLOCK">Block</option>
        </select>
      </div>

      {error && <p className="text-signal-danger text-sm font-mono">{error}</p>}

      {!cases && !error && (
        <div className="flex items-center gap-2 text-slate-500 text-sm font-mono">
          <Loader2 className="animate-spin" size={16} /> Loading cases…
        </div>
      )}

      {cases && filtered.length === 0 && (
        <div className="rounded-xl border border-dashed border-base-600 py-16 text-center">
          <p className="text-slate-400 text-sm">
            {cases.length === 0
              ? 'No cases yet. Analyze an email or connect Gmail to get started.'
              : 'No cases match this filter.'}
          </p>
        </div>
      )}

      {cases && filtered.length > 0 && (
        <div className="rounded-xl border border-base-700 overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-base-800 text-left text-[11px] font-mono uppercase tracking-widest text-slate-500">
                <th className="px-4 py-3 font-medium">Case ID</th>
                <th className="px-4 py-3 font-medium">Subject</th>
                <th className="px-4 py-3 font-medium">From</th>
                <th className="px-4 py-3 font-medium">Source</th>
                <th className="px-4 py-3 font-medium">Classification</th>
                <th className="px-4 py-3 font-medium">Risk</th>
                <th className="px-4 py-3 font-medium">Decision</th>
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((c) => (
                <tr key={c.case_id} className="border-t border-base-700 hover:bg-base-800/60">
                  <td className="px-4 py-3 font-mono text-xs text-trace">{c.case_id}</td>
                  <td className="px-4 py-3 text-slate-300 max-w-[220px] truncate">{c.subject || '—'}</td>
                  <td className="px-4 py-3 text-slate-400 font-mono text-xs max-w-[180px] truncate">{c.from_address}</td>
                  <td className="px-4 py-3 text-slate-500 text-xs">
                    {c.source === 'gmail' ? (
                      <span className="inline-flex items-center gap-1"><Mail size={12} /> Gmail</span>
                    ) : (
                      <span className="inline-flex items-center gap-1"><UploadCloud size={12} /> Upload</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-slate-400 font-mono text-xs">{c.classification}</td>
                  <td className="px-4 py-3 font-mono text-xs text-slate-200">{c.final_risk_score}</td>
                  <td className="px-4 py-3">
                    <span className={`text-[10px] px-2 py-0.5 rounded border font-mono ${decisionStyle[c.decision] || ''}`}>
                      {c.decision}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <Link to={`/cases/${c.case_id}`} className="inline-flex items-center gap-1 text-xs text-slate-500 hover:text-trace">
                      View <ChevronRight size={13} />
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {uploadOpen && <UploadModal onClose={() => setUploadOpen(false)} />}
    </div>
  )
}
