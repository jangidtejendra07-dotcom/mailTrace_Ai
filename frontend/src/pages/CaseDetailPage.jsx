import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { ChevronLeft, Loader2 } from 'lucide-react'
import { getCase } from '../lib/api.js'
import ResultPanel from '../components/ResultPanel.jsx'

export default function CaseDetailPage() {
  const { caseId } = useParams()
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    getCase(caseId).then(setResult).catch(() => setError('Case not found'))
  }, [caseId])

  return (
    <div className="max-w-7xl mx-auto px-8 py-10">
      <Link to="/cases" className="inline-flex items-center gap-1 text-xs font-mono text-slate-500 hover:text-trace mb-6">
        <ChevronLeft size={14} /> Back to Case Vault
      </Link>

      {error && <p className="text-signal-danger text-sm font-mono">{error}</p>}
      {!result && !error && (
        <div className="flex items-center gap-2 text-slate-500 text-sm font-mono"><Loader2 className="animate-spin" size={16} /> Loading case {caseId}…</div>
      )}
      {result && <ResultPanel result={result} />}
    </div>
  )
}
