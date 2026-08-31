import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { FolderClock, ChevronRight, Loader2 } from 'lucide-react'
import { listCases } from '../lib/api.js'

const decisionStyle = {
  ALLOW: 'text-signal-safe bg-signal-safe/10 border-signal-safe/30',
  QUARANTINE: 'text-signal-watch bg-signal-watch/10 border-signal-watch/30',
  BLOCK: 'text-signal-critical bg-signal-critical/10 border-signal-critical/30',
}

export default function CasesPage() {
  const [cases, setCases] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    listCases().then(setCases).catch(() => setError('Could not reach backend on :8000'))
  }, [])

  return (
    <div className="max-w-6xl mx-auto px-8 py-10">
      <header className="mb-8 flex items-center gap-3">
        <FolderClock className="text-trace" size={22} />
        <div>
          <h1 className="font-display text-2xl font-semibold text-slate-50">Case Vault</h1>
          <p className="text-sm text-slate-400 mt-0.5">Every quarantined or blocked message, with evidence and forensic reports.</p>
        </div>
      </header>

      {error && <p className="text-signal-danger text-sm font-mono">{error}</p>}

      {!cases && !error && (
        <div className="flex items-center gap-2 text-slate-500 text-sm font-mono"><Loader2 className="animate-spin" size={16} /> Loading cases…</div>
      )}

      {cases && cases.length === 0 && (
        <div className="rounded-xl border border-dashed border-base-600 py-16 text-center">
          <p className="text-slate-400 text-sm">No cases yet. Analyze an email to populate the vault.</p>
        </div>
      )}

      {cases && cases.length > 0 && (
        <div className="rounded-xl border border-base-700 overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-base-800 text-left text-[11px] font-mono uppercase tracking-widest text-slate-500">
                <th className="px-4 py-3 font-medium">Case ID</th>
                <th className="px-4 py-3 font-medium">Subject</th>
                <th className="px-4 py-3 font-medium">From</th>
                <th className="px-4 py-3 font-medium">Classification</th>
                <th className="px-4 py-3 font-medium">Risk</th>
                <th className="px-4 py-3 font-medium">Decision</th>
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody>
              {cases.map((c) => (
                <tr key={c.case_id} className="border-t border-base-700 hover:bg-base-800/60">
                  <td className="px-4 py-3 font-mono text-xs text-trace">{c.case_id}</td>
                  <td className="px-4 py-3 text-slate-300 max-w-[220px] truncate">{c.subject || '—'}</td>
                  <td className="px-4 py-3 text-slate-400 font-mono text-xs max-w-[180px] truncate">{c.from_address}</td>
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
    </div>
  )
}
