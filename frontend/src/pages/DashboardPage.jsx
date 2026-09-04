import { useEffect, useState, useCallback, useRef } from 'react'
import { Link } from 'react-router-dom'
import {
  LayoutDashboard, Mail, ShieldAlert, TriangleAlert, ChevronRight, Loader2, PieChart, BarChart3,
} from 'lucide-react'
import { listCases, listQuarantinedCases, getGmailStatus, syncGmail, startRealtimeWatch } from '../lib/api.js'
import PageHeader from '../components/PageHeader.jsx'
import StatCard from '../components/StatCard.jsx'
import DonutChart from '../components/DonutChart.jsx'
import CategoryBars from '../components/CategoryBars.jsx'
import GmailStatusCard from '../components/GmailStatusCard.jsx'
import Panel from '../components/Panel.jsx'

const POLL_MS = 20000

const decisionStyle = {
  ALLOW: 'text-signal-safe bg-signal-safe/10 border-signal-safe/30',
  QUARANTINE: 'text-signal-watch bg-signal-watch/10 border-signal-watch/30',
  BLOCK: 'text-signal-critical bg-signal-critical/10 border-signal-critical/30',
}

const CATEGORY_COLORS = {
  phishing: '#ff5d5d',
  bec: '#f5b942',
  malware: '#ff2d55',
  spam: '#7c9cff',
  malicious: '#ff2d55',
  suspicious: '#f5b942',
}

function titleCase(s) {
  if (!s) return 'Unknown'
  return s.charAt(0).toUpperCase() + s.slice(1)
}

export default function DashboardPage() {
  const [cases, setCases] = useState(null)
  const [quarantined, setQuarantined] = useState(null)
  const [gmailStatus, setGmailStatus] = useState(null)
  const [syncing, setSyncing] = useState(false)
  const [error, setError] = useState(null)
  const firstLoad = useRef(true)

  const loadAll = useCallback(async () => {
    try {
      const [casesData, quarantinedData, statusData] = await Promise.all([
        listCases(),
        listQuarantinedCases(),
        getGmailStatus(),
      ])
      setCases(casesData)
      setQuarantined(quarantinedData)
      setGmailStatus(statusData)
      setError(null)
    } catch {
      if (firstLoad.current) setError('Could not reach the MailTrace backend.')
    } finally {
      firstLoad.current = false
    }
  }, [])

  useEffect(() => {
    loadAll()
    const interval = setInterval(loadAll, POLL_MS)
    return () => clearInterval(interval)
  }, [loadAll])

  // If Gmail is connected but real-time detection isn't on yet, enable it
  // automatically so the user doesn't have to find the toggle in Settings.
  useEffect(() => {
    if (!gmailStatus?.connected || gmailStatus.realtime_enabled) return
    let cancelled = false
    startRealtimeWatch()
      .then(() => { if (!cancelled) loadAll() })
      .catch(() => {}) // silent — real-time detection is an enhancement, not required
    return () => { cancelled = true }
  }, [gmailStatus?.connected, gmailStatus?.realtime_enabled, loadAll])

  async function handleSync() {
    setSyncing(true)
    try {
      await syncGmail()
      await loadAll()
    } catch {
      // Sync errors are surfaced in detail on the Settings page; keep the
      // dashboard quiet so a transient failure doesn't block the whole view.
    } finally {
      setSyncing(false)
    }
  }

  const loading = cases === null && !error

  const totalEmails = cases?.length ?? 0
  const threats = cases?.filter((c) => c.decision !== 'ALLOW').length ?? 0
  const highRisk = cases?.filter((c) => (c.final_risk_score ?? 0) >= 75).length ?? 0
  const quarantinedCount = quarantined?.length ?? 0

  const riskSegments = [
    { label: 'Safe', value: cases?.filter((c) => c.decision === 'ALLOW').length ?? 0, color: '#2dd4a7' },
    { label: 'Medium', value: cases?.filter((c) => c.decision === 'QUARANTINE').length ?? 0, color: '#f5b942' },
    { label: 'High', value: cases?.filter((c) => c.decision === 'BLOCK').length ?? 0, color: '#ff2d55' },
  ]

  const categoryCounts = {}
  cases?.forEach((c) => {
    const cat = (c.classification || '').toLowerCase()
    if (!cat || cat === 'safe') return
    categoryCounts[cat] = (categoryCounts[cat] || 0) + 1
  })
  const categoryItems =
    Object.keys(categoryCounts).length > 0
      ? Object.entries(categoryCounts)
          .sort((a, b) => b[1] - a[1])
          .map(([label, value]) => ({ label: titleCase(label), value, color: CATEGORY_COLORS[label] || '#7c9cff' }))
      : [
          { label: 'Phishing', value: 0, color: CATEGORY_COLORS.phishing },
          { label: 'BEC', value: 0, color: CATEGORY_COLORS.bec },
          { label: 'Malware', value: 0, color: CATEGORY_COLORS.malware },
          { label: 'Spam', value: 0, color: CATEGORY_COLORS.spam },
        ]

  const recent = (cases || []).slice(0, 7)
  const quarantineSnapshot = (quarantined || []).slice(0, 3)

  return (
    <div className="max-w-7xl mx-auto px-8 py-10">
      <PageHeader
        icon={LayoutDashboard}
        title="Dashboard"
        subtitle="Live overview of every email MailTrace has analyzed — across manual uploads and your connected Gmail inbox."
      />

      {error && <p className="text-signal-danger text-sm font-mono mb-6">{error}</p>}

      {loading ? (
        <div className="flex items-center gap-2 text-slate-500 text-sm font-mono">
          <Loader2 className="animate-spin" size={16} /> Loading dashboard…
        </div>
      ) : (
        <div className="space-y-6">
          <GmailStatusCard status={gmailStatus} syncing={syncing} onSync={handleSync} />

          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <StatCard icon={Mail} label="Total Emails" value={totalEmails} accent="trace" />
            <StatCard icon={TriangleAlert} label="Threats Detected" value={threats} accent="watch" />
            <StatCard icon={ShieldAlert} label="High Risk" value={highRisk} accent="danger" />
            <StatCard icon={ShieldAlert} label="Quarantined" value={quarantinedCount} accent="wire" />
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
            <Panel title="Risk Distribution" icon={PieChart}>
              <DonutChart segments={riskSegments} />
            </Panel>
            <Panel title="Threat Categories" icon={BarChart3}>
              <CategoryBars items={categoryItems} />
            </Panel>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
            <Panel title="Recent Analyses" className="lg:col-span-2" right={
              <Link to="/cases" className="text-xs text-slate-500 hover:text-trace inline-flex items-center gap-1">
                View all <ChevronRight size={12} />
              </Link>
            }>
              {recent.length === 0 ? (
                <p className="text-xs text-slate-500 font-mono py-4 text-center">
                  No emails analyzed yet — upload one from the Cases page or connect Gmail.
                </p>
              ) : (
                <div className="divide-y divide-base-700">
                  {recent.map((c) => (
                    <Link
                      key={c.case_id}
                      to={`/cases/${c.case_id}`}
                      className="flex items-center justify-between gap-3 py-2.5 first:pt-0 last:pb-0 hover:opacity-80 transition-opacity"
                    >
                      <div className="min-w-0">
                        <p className="text-sm text-slate-300 truncate">{c.subject || '(no subject)'}</p>
                        <p className="text-xs text-slate-500 font-mono truncate">{c.from_address}</p>
                      </div>
                      <span className={`text-[10px] px-2 py-0.5 rounded border font-mono shrink-0 ${decisionStyle[c.decision] || ''}`}>
                        {c.decision}
                      </span>
                    </Link>
                  ))}
                </div>
              )}
            </Panel>

            <Panel title="Quarantine" icon={ShieldAlert} right={
              <Link to="/quarantine" className="text-xs text-slate-500 hover:text-trace inline-flex items-center gap-1">
                View all <ChevronRight size={12} />
              </Link>
            }>
              {quarantineSnapshot.length === 0 ? (
                <p className="text-xs text-slate-500 font-mono py-4 text-center">Nothing quarantined right now.</p>
              ) : (
                <div className="space-y-3">
                  {quarantineSnapshot.map((c) => (
                    <Link key={c.case_id} to={`/cases/${c.case_id}`} className="block hover:opacity-80 transition-opacity">
                      <p className="text-xs text-slate-300 truncate">{c.subject || '(no subject)'}</p>
                      <p className="text-[11px] text-slate-500 font-mono truncate">{(c.reasons || [])[0] || c.from_address}</p>
                    </Link>
                  ))}
                </div>
              )}
            </Panel>
          </div>
        </div>
      )}
    </div>
  )
}
