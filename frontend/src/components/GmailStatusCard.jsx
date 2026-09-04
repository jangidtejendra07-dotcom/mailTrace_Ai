import { Link } from 'react-router-dom'
import { Mail, RefreshCw, Loader2, Radar, ArrowUpRight } from 'lucide-react'

export default function GmailStatusCard({ status, syncing, onSync }) {
  if (!status) {
    return (
      <div className="rounded-xl border border-base-700 bg-base-900/60 backdrop-blur-sm p-4 flex items-center gap-2 text-xs font-mono text-slate-500">
        <Loader2 className="animate-spin" size={14} /> Checking Gmail status…
      </div>
    )
  }

  if (!status.connected) {
    return (
      <div className="rounded-xl border border-dashed border-base-600 bg-base-900/40 p-4 flex items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <Mail className="text-slate-500" size={18} />
          <div>
            <p className="text-sm font-medium text-slate-300">Gmail not connected</p>
            <p className="text-xs text-slate-500">Connect an inbox to enable live threat detection.</p>
          </div>
        </div>
        <Link
          to="/settings"
          className="inline-flex items-center gap-1.5 rounded-lg border border-trace/40 bg-trace/10 text-trace text-xs font-medium px-3.5 py-2 hover:bg-trace/20 transition-colors shrink-0"
        >
          Connect <ArrowUpRight size={13} />
        </Link>
      </div>
    )
  }

  return (
    <div className="rounded-xl border border-base-700 bg-base-900/60 backdrop-blur-sm p-4 flex items-center justify-between gap-4">
      <div className="flex items-center gap-3 min-w-0">
        <div
          className={`w-9 h-9 rounded-lg border flex items-center justify-center shrink-0 ${
            status.realtime_enabled
              ? 'text-signal-safe bg-signal-safe/10 border-signal-safe/30'
              : 'text-slate-400 bg-base-800 border-base-600'
          }`}
        >
          <Radar size={16} strokeWidth={2} />
        </div>
        <div className="min-w-0">
          <p className="text-sm font-medium text-slate-200 truncate">{status.gmail_address}</p>
          <p className="text-xs text-slate-500 font-mono">
            {status.realtime_enabled ? 'Real-time protection ON' : 'Real-time protection OFF'}
            {status.last_synced_at ? ` · last synced ${new Date(status.last_synced_at).toLocaleTimeString()}` : ''}
          </p>
        </div>
      </div>
      <div className="flex items-center gap-2 shrink-0">
        <button
          onClick={onSync}
          disabled={syncing}
          className="inline-flex items-center gap-1.5 rounded-lg border border-trace/40 bg-trace/10 text-trace text-xs font-medium px-3 py-2 hover:bg-trace/20 transition-colors disabled:opacity-60"
        >
          {syncing ? <Loader2 size={13} className="animate-spin" /> : <RefreshCw size={13} />}
          Sync now
        </button>
        <Link
          to="/settings"
          className="inline-flex items-center gap-1 text-xs text-slate-500 hover:text-trace px-1"
        >
          Manage
        </Link>
      </div>
    </div>
  )
}
