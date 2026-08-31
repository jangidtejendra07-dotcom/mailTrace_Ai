import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { ShieldAlert, ChevronRight, Loader2, Undo2 } from 'lucide-react'
import { listQuarantinedCases, releaseCase } from '../lib/api.js'

const decisionStyle = {
  QUARANTINE: 'text-signal-watch bg-signal-watch/10 border-signal-watch/30',
  BLOCK: 'text-signal-critical bg-signal-critical/10 border-signal-critical/30',
}

export default function QuarantinePage() {
  const [cases, setCases] = useState(null)
  const [error, setError] = useState(null)
  const [releasingId, setReleasingId] = useState(null)

  function load() {
    listQuarantinedCases().then(setCases).catch(() => setError('Could not reach backend on :8000'))
  }

  useEffect(load, [])

  async function handleRelease(caseId) {
    setReleasingId(caseId)
    try {
      await releaseCase(caseId)
      setCases((prev) => prev.filter((c) => c.case_id !== caseId))
    } catch (err) {
      setError(err?.response?.data?.detail || 'Could not release this message.')
    } finally {
      setReleasingId(null)
    }
  }

  return (
    <div className="max-w-6xl mx-auto px-8 py-10">
      <header className="mb-8 flex items-center gap-3">
        <ShieldAlert className="text-signal-critical" size={22} />
        <div>
          <h1 className="font-display text-2xl font-semibold text-slate-50">Quarantined mail</h1>
          <p className="text-sm text-slate-400 mt-0.5">
            High-risk mail automatically pulled out of your Gmail inbox. Nothing is deleted —
            review it here and release it back to your inbox if it's a false positive.
          </p>
        </div>
      </header>

      {error && <p className="text-signal-danger text-sm font-mono mb-4">{error}</p>}

      {!cases && !error && (
        <div className="flex items-center gap-2 text-slate-500 text-sm font-mono">
          <Loader2 className="animate-spin" size={16} /> Loading quarantined mail…
        </div>
      )}

      {cases && cases.length === 0 && (
        <div className="rounded-xl border border-dashed border-base-600 py-16 text-center">
          <p className="text-slate-400 text-sm">
            Nothing quarantined right now — high-risk mail will show up here automatically.
          </p>
        </div>
      )}

      {cases && cases.length > 0 && (
        <div className="rounded-xl border border-base-700 overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-base-800 text-left text-[11px] font-mono uppercase tracking-widest text-slate-500">
                <th className="px-4 py-3 font-medium">Subject</th>
                <th className="px-4 py-3 font-medium">From</th>
                <th className="px-4 py-3 font-medium">Why</th>
                <th className="px-4 py-3 font-medium">Risk</th>
                <th className="px-4 py-3 font-medium">Decision</th>
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody>
              {cases.map((c) => (
                <tr key={c.case_id} className="border-t border-base-700 hover:bg-base-800/60">
                  <td className="px-4 py-3 text-slate-300 max-w-[200px] truncate">{c.subject || '—'}</td>
                  <td className="px-4 py-3 text-slate-400 font-mono text-xs max-w-[160px] truncate">{c.from_address}</td>
                  <td className="px-4 py-3 text-slate-400 text-xs max-w-[240px] truncate" title={(c.reasons || []).join('; ')}>
                    {(c.reasons || [])[0] || '—'}
                  </td>
                  <td className="px-4 py-3 font-mono text-xs text-slate-200">{c.final_risk_score}</td>
                  <td className="px-4 py-3">
                    <span className={`text-[10px] px-2 py-0.5 rounded border font-mono ${decisionStyle[c.decision] || ''}`}>
                      {c.decision}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right whitespace-nowrap">
                    <button
                      onClick={() => handleRelease(c.case_id)}
                      disabled={releasingId === c.case_id}
                      className="inline-flex items-center gap-1 text-xs text-slate-400 hover:text-trace mr-3 disabled:opacity-50"
                    >
                      <Undo2 size={13} /> {releasingId === c.case_id ? 'Releasing…' : 'Release to inbox'}
                    </button>
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
