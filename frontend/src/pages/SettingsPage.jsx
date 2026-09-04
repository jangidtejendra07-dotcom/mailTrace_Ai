import { useEffect, useState, useCallback } from 'react'
import { useSearchParams } from 'react-router-dom'
import {
  Settings as SettingsIcon, Mail, RefreshCw, Unplug, Loader2, CheckCircle2, ShieldAlert, Radar, User,
} from 'lucide-react'
import {
  getGmailStatus, getGmailAuthUrl, syncGmail, disconnectGmail,
  startRealtimeWatch, stopRealtimeWatch,
} from '../lib/api.js'
import { useAuth } from '../context/AuthContext.jsx'
import PageHeader from '../components/PageHeader.jsx'
import Panel from '../components/Panel.jsx'

export default function SettingsPage() {
  const { user } = useAuth()
  const [searchParams] = useSearchParams()
  const [status, setStatus] = useState(null)
  const [connecting, setConnecting] = useState(false)
  const [syncing, setSyncing] = useState(false)
  const [error, setError] = useState(null)
  const [syncSummary, setSyncSummary] = useState(null)
  const [watchLoading, setWatchLoading] = useState(false)

  const loadStatus = useCallback(() => {
    getGmailStatus().then(setStatus).catch(() => setError('Could not load Gmail status'))
  }, [])

  useEffect(() => { loadStatus() }, [loadStatus])

  useEffect(() => {
    if (searchParams.get('gmail_connected') === '1') loadStatus()
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
    <div className="max-w-3xl mx-auto px-8 py-10">
      <PageHeader icon={SettingsIcon} title="Settings" subtitle="Manage your MailTrace profile and Gmail integration." />

      <div className="space-y-6">
        <Panel title="Profile" icon={User}>
          <div className="space-y-1">
            <p className="text-sm font-medium text-slate-200">{user?.full_name || '(no name set)'}</p>
            <p className="text-xs text-slate-500 font-mono">{user?.email}</p>
          </div>
        </Panel>

        <Panel title="Gmail Integration" icon={Mail}>
          {!status && !error && (
            <div className="flex items-center gap-2 text-slate-500 text-sm font-mono">
              <Loader2 className="animate-spin" size={16} /> Checking connection…
            </div>
          )}

          {status && !status.connected && (
            <div className="text-center py-8 px-4">
              <Mail className="mx-auto text-trace mb-4" size={30} strokeWidth={1.6} />
              <p className="font-medium text-slate-200 mb-1.5">No Gmail account connected yet</p>
              <p className="text-sm text-slate-500 max-w-md mx-auto mb-6">
                You'll be redirected to Google to grant access. MailTrace never sends or deletes mail — it
                only reads and labels messages to detect and quarantine threats.
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
              <div className="flex items-center justify-between gap-3 mb-4 flex-wrap">
                <div className="flex items-center gap-3">
                  <CheckCircle2 className="text-signal-safe" size={20} />
                  <div>
                    <p className="text-sm font-medium text-slate-200">{status.gmail_address}</p>
                    <p className="text-xs text-slate-500 font-mono">
                      {status.last_synced_at ? `Last synced ${new Date(status.last_synced_at).toLocaleString()}` : 'Never synced yet'}
                    </p>
                  </div>
                </div>
                <button
                  onClick={handleDisconnect}
                  className="inline-flex items-center gap-2 rounded-lg border border-base-600 text-slate-400 text-xs font-medium px-3.5 py-2 hover:bg-base-800 transition-colors"
                >
                  <Unplug size={14} /> Disconnect
                </button>
              </div>

              <div className="flex items-center gap-2 flex-wrap mb-4">
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
              </div>

              {status.realtime_enabled && (
                <div className="mb-4 flex items-center gap-2 text-xs text-signal-safe bg-signal-safe/10 border border-signal-safe/30 rounded-lg px-4 py-2.5">
                  <Radar size={14} /> Real-time detection is on — new mail is analyzed automatically within seconds of arriving.
                </div>
              )}

              {syncSummary && (
                <div className="mb-4 text-xs font-mono text-slate-400 bg-base-800/60 border border-base-700 rounded-lg px-4 py-2.5">
                  Fetched {syncSummary.fetched} · Analyzed {syncSummary.new_cases} new · Skipped {syncSummary.skipped_existing} already-seen
                </div>
              )}
            </>
          )}

          {error && (
            <div className="mt-2 flex items-center gap-2 text-xs text-signal-danger bg-signal-danger/10 border border-signal-danger/30 rounded-lg px-4 py-2.5">
              <ShieldAlert size={14} /> {error}
            </div>
          )}
        </Panel>
      </div>
    </div>
  )
}
