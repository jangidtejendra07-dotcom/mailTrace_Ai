import { useEffect, useState, useCallback } from 'react'
import { Link2 as ChainIcon, Loader2, RefreshCw, CheckCircle2, CircleSlash, XCircle } from 'lucide-react'
import Panel from './Panel.jsx'
import { verifyCaseBlockchain } from '../lib/api.js'

const STATUS_META = {
  verified: { icon: CheckCircle2, color: 'text-signal-safe', label: 'Verified on-chain' },
  recorded: { icon: CheckCircle2, color: 'text-signal-safe', label: 'Recorded on-chain' },
  not_found: { icon: XCircle, color: 'text-signal-watch', label: 'Not found on-chain' },
  failed: { icon: XCircle, color: 'text-signal-danger', label: 'Verification failed' },
  disabled: { icon: CircleSlash, color: 'text-slate-500', label: 'Blockchain auditing disabled' },
}

export default function BlockchainPanel({ caseId }) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const load = useCallback(() => {
    setLoading(true)
    setError(null)
    verifyCaseBlockchain(caseId)
      .then(setData)
      .catch((e) => setError(e?.response?.data?.detail || 'Could not check blockchain status.'))
      .finally(() => setLoading(false))
  }, [caseId])

  useEffect(() => { load() }, [load])

  const status = data?.blockchain_status || data?.verification?.status
  const meta = STATUS_META[status] || STATUS_META.disabled
  const StatusIcon = meta.icon

  return (
    <Panel
      title="Blockchain Evidence"
      icon={ChainIcon}
      right={
        <button onClick={load} disabled={loading} className="text-slate-500 hover:text-trace transition-colors disabled:opacity-50">
          <RefreshCw size={13} className={loading ? 'animate-spin' : ''} />
        </button>
      }
    >
      {loading && !data ? (
        <div className="flex items-center gap-2 text-xs font-mono text-slate-500">
          <Loader2 className="animate-spin" size={13} /> Checking chain…
        </div>
      ) : error ? (
        <p className="text-xs text-signal-danger">{error}</p>
      ) : (
        <div className="space-y-2.5">
          <div className={`flex items-center gap-2 text-sm font-medium ${meta.color}`}>
            <StatusIcon size={16} /> {meta.label}
          </div>
          {status === 'disabled' && (
            <p className="text-xs text-slate-500">
              On-chain auditing isn't configured for this deployment. Evidence integrity is still guaranteed via the
              SHA-256 hash below.
            </p>
          )}
          {data?.blockchain_transaction && (
            <div className="text-xs font-mono text-slate-500 break-all">
              Tx: <span className="text-slate-300">{data.blockchain_transaction}</span>
            </div>
          )}
          {data?.local_evidence_hash && (
            <div className="text-xs font-mono text-slate-500 break-all">
              Evidence hash: <span className="text-slate-300">{data.local_evidence_hash}</span>
            </div>
          )}
        </div>
      )}
    </Panel>
  )
}
