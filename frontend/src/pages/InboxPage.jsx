import { useEffect, useState, useCallback } from 'react'
import { useSearchParams, Link } from 'react-router-dom'
import {
  Mail, RefreshCw, Unplug, Loader2, ChevronRight, CheckCircle2, ShieldAlert, Inbox as InboxIcon, Radar,
} from 'lucide-react'
import {
  getGmailStatus, getGmailAuthUrl, syncGmail, disconnectGmail, listCases,
  startRealtimeWatch, stopRealtimeWatch,
} from '../lib/api.js'

const decisionStyle = {
  ALLOW: 'text-signal-safe bg-signal-safe/10 border-signal-safe/30',
  QUARANTINE: 'text-signal-watch bg-signal-watch/10 border-signal-watch/30',
  BLOCK: 'text-signal-critical bg-signal-critical/10 border-signal-critical/30',
}

export default function InboxPage() {
  const [searchParams] = useSearchParams()
  const [status, setStatus] = useState(null)
  const [connecting, setConnecting] = useState(false)
  const [syncing, setSyncing] = useState(false)
  const [error, setError] = useState(null)
  const [cases, setCases] = useState(null)
  const [syncSummary, setSyncSummary] = useState(null)
  const [watchLoading, setWatchLoading] = useState(false)

  const loadStatus = useCallback(() => {
    getGmailStatus().then(setStatus).catch(() => setError('Could not load Gmail status'))
  }, [])

  const loadCases = useCallback(() => {
    listCases().then((all) => setCases(all.filter((c) => c.source === 'gmail'))).catch(() => {})
  }, [])

  useEffect(() => {
    loadStatus()
    loadCases()
  }, [loadStatus, loadCases])

  // After Gmail is connected, automatically enable the backend watch.
  // This removes the need for the user to click "Turn on real-time".
  // The backend remains responsible for processing incoming mail.
  useEffect(() => {
    if (!status?.connected || status.realtime_enabled || watchLoading) return

    let cancelled = false

    async function enableRealtimeAutomatically() {
      setWatchLoading(true)
      setError(null)

      try {
        await startRealtimeWatch()
        if (!cancelled) await loadStatus()
      } catch (err) {
        if (!cancelled) {
          setError(
            err?.response?.data?.detail ||
            'Could not enable real-time Gmail detection automatically.'
          )
        }
      } finally {
        if (!cancelled) setWatchLoading(false)
      }
    }

    enableRealtimeAutomatically()

    return () => {
      cancelled = true
    }
  }, [status?.connected, status?.realtime_enabled, watchLoading, loadStatus])

  useEffect(() => {
    if (searchParams.get('gmail_connected') === '1') {
      loadStatus()
    }
  }, [searchParams, loadStatus])

  async function handleConnect() {
    setError(null)
    setConnecting(true)
    try {
      const { authorization_url } = await getGmailAuthUrl()
      window.location.href = authorization_url
    } catch (err) {
      setError(err?.response?.data?.detail || 'Gmail integration is not configured on the server yet.')
      setConnecting(false)
    }
  }

  async function handleSync() {
    setError(null)
    setSyncing(true)
    setSyncSummary(null)
    try {
      const result = await syncGmail()
      setSyncSummary(result)
      loadCases()
      loadStatus()
    } catch (err) {
      setError(err?.response?.data?.detail || 'Sync failed.')
    } finally {
      setSyncing(false)
    }
  }

  async function handleDisconnect() {
    await disconnectGmail()
    loadStatus()
    setCases([])
  }

  async function handleToggleRealtime() {
    setError(null)
    setWatchLoading(true)
    try {
      if (status.realtime_enabled) {
        await stopRealtimeWatch()
      } else {
        await startRealtimeWatch()
      }
      loadStatus()
    } catch (err) {
      setError(err?.response?.data?.detail || 'Could not change real-time detection setting.')
    } finally {
      setWatchLoading(false)
    }
  }

  return (
    <div className="max-w-6xl mx-auto px-8 py-10">
      <header className="mb-8 flex items-center gap-3">
        <InboxIcon className="text-trace" size={22} />
        <div>
          <h1 className="font-display text-2xl font-semibold text-slate-50">Live Gmail Inbox</h1>
          <p className="text-sm text-slate-400 mt-0.5">Connect a Gmail account and run every incoming message through the detection pipeline.</p>
        </div>
      </header>

      {!status && !error && (
        <div className="flex items-center gap-2 text-slate-500 text-sm font-mono"><Loader2 className="animate-spin" size={16} /> Checking connection…</div>
      )}

      {status && !status.connected && (
        <div className="rounded-2xl border border-dashed border-base-600 py-16 px-6 text-center bg-base-900/40">
          <Mail className="mx-auto text-trace mb-4" size={32} strokeWidth={1.6} />
          <p className="font-medium text-slate-200 mb-1.5">No Gmail account connected yet</p>
          <p className="text-sm text-slate-500 max-w-md mx-auto mb-6">
            You'll be redirected to Google to grant read-only access to your inbox.
            MailTrace never sends or deletes mail — it only reads messages to analyze them.
          </p>
          <button
            onClick={handleConnect}
            disabled={connecting}
            className="inline-flex items-center gap-2 rounded-lg bg-trace text-base-950 font-semibold text-sm px-5 py-2.5 hover:bg-trace/90 transition-colors disabled:opacity-60"
          >
            {connecting ? <Loader2 size={16} className="animate-spin" /> : <Mail size={16} />}
            Connect Gmail
          </button>
        </div>
      )}

      {status && status.connected && (
        <>
          <div className="rounded-xl border border-base-700 bg-base-900/60 px-5 py-4 flex items-center justify-between mb-6">
            <div className="flex items-center gap-3">
              <CheckCircle2 className="text-signal-safe" size={20} />
              <div>
                <p className="text-sm font-medium text-slate-200">{status.gmail_address}</p>
                <p className="text-xs text-slate-500 font-mono">
                  {status.last_synced_at ? `Last synced ${new Date(status.last_synced_at).toLocaleString()}` : 'Never synced yet'}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={handleSync}
                disabled={syncing}
                className="inline-flex items-center gap-2 rounded-lg border border-trace/40 bg-trace/10 text-trace text-xs font-medium px-3.5 py-2 hover:bg-trace/20 transition-colors disabled:opacity-60"
              >
                {syncing ? <Loader2 size={14} className="animate-spin" /> : <RefreshCw size={14} />}
                Sync Gmail
              </button>
              <button
                onClick={handleToggleRealtime}
                disabled={watchLoading}
                title={status.realtime_enabled ? 'New mail is auto-analyzed the moment it arrives' : 'Turn on to analyze new mail automatically, without clicking Sync'}
                className={`inline-flex items-center gap-2 rounded-lg border text-xs font-medium px-3.5 py-2 transition-colors disabled:opacity-60 ${
                  status.realtime_enabled
                    ? 'border-signal-safe/40 bg-signal-safe/10 text-signal-safe hover:bg-signal-safe/20'
                    : 'border-base-600 text-slate-400 hover:bg-base-800'
                }`}
              >
                {watchLoading ? <Loader2 size={14} className="animate-spin" /> : <Radar size={14} />}
                {status.realtime_enabled ? 'Real-time: ON' : 'Turn on real-time'}
              </button>
              <button
                onClick={handleDisconnect}
                className="inline-flex items-center gap-2 rounded-lg border border-base-600 text-slate-400 text-xs font-medium px-3.5 py-2 hover:bg-base-800 transition-colors"
              >
                <Unplug size={14} /> Disconnect
              </button>
            </div>
          </div>

          {status.realtime_enabled && (
            <div className="mb-6 flex items-center gap-2 text-xs text-signal-safe bg-signal-safe/10 border border-signal-safe/30 rounded-lg px-4 py-2.5">
              <Radar size={14} /> Real-time detection is on — new mail is analyzed automatically within seconds of arriving, no need to click Sync.
            </div>
          )}

          {syncSummary && (
            <div className="mb-6 text-xs font-mono text-slate-400 bg-base-800/60 border border-base-700 rounded-lg px-4 py-2.5">
              Fetched {syncSummary.fetched} · Analyzed {syncSummary.new_cases} new · Skipped {syncSummary.skipped_existing} already-seen
            </div>
          )}

          {error && (
            <div className="mb-6 flex items-center gap-2 text-xs text-signal-danger bg-signal-danger/10 border border-signal-danger/30 rounded-lg px-4 py-2.5">
              <ShieldAlert size={14} /> {error}
            </div>
          )}

          {cases && cases.length === 0 && (
            <div className="rounded-xl border border-dashed border-base-600 py-12 text-center">
              <p className="text-slate-400 text-sm">No Gmail-sourced cases yet. Click "Sync Gmail" to pull and analyze your recent inbox.</p>
            </div>
          )}

          {cases && cases.length > 0 && (
            <div className="rounded-xl border border-base-700 overflow-hidden">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-base-800 text-left text-[11px] font-mono uppercase tracking-widest text-slate-500">
                    <th className="px-4 py-3 font-medium">Subject</th>
                    <th className="px-4 py-3 font-medium">From</th>
                    <th className="px-4 py-3 font-medium">Risk</th>
                    <th className="px-4 py-3 font-medium">Decision</th>
                    <th className="px-4 py-3"></th>
                  </tr>
                </thead>
                <tbody>
                  {cases.map((c) => (
                    <tr key={c.case_id} className="border-t border-base-700 hover:bg-base-800/60">
                      <td className="px-4 py-3 text-slate-300 max-w-[260px] truncate">{c.subject || '—'}</td>
                      <td className="px-4 py-3 text-slate-400 font-mono text-xs max-w-[200px] truncate">{c.from_address}</td>
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
        </>
      )}
    </div>
  )
}
