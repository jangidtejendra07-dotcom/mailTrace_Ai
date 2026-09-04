import { useState } from 'react'
import {
  BrainCircuit, FileSearch2, Link2, Paperclip, MapPinned,
  GitBranch, AlertTriangle, ShieldCheck, Undo2, Loader2, Waypoints,
} from 'lucide-react'
import { Link } from 'react-router-dom'
import RiskGauge from './RiskGauge.jsx'
import ScoreBar from './ScoreBar.jsx'
import Panel from './Panel.jsx'
import GeoMap from './GeoMap.jsx'
import RecommendationPanel from './RecommendationPanel.jsx'
import BlockchainPanel from './BlockchainPanel.jsx'
import LegalReportButtons from './LegalReportButtons.jsx'
import { releaseCase } from '../lib/api.js'

const sevColor = {
  LOW: 'text-signal-safe border-signal-safe/40 bg-signal-safe/10',
  MEDIUM: 'text-signal-watch border-signal-watch/40 bg-signal-watch/10',
  HIGH: 'text-signal-danger border-signal-danger/40 bg-signal-danger/10',
  CRITICAL: 'text-signal-critical border-signal-critical/40 bg-signal-critical/10',
}

const authColor = (v) => (v === 'pass' ? 'text-signal-safe' : v === 'fail' ? 'text-signal-danger' : 'text-signal-watch')

export default function ResultPanel({ result }) {
  const [releaseState, setReleaseState] = useState('idle') // idle | loading | released | error
  const [releaseError, setReleaseError] = useState(null)

  if (!result) return null

  async function handleRelease() {
    setReleaseState('loading')
    setReleaseError(null)
    try {
      await releaseCase(result.case_id)
      setReleaseState('released')
    } catch (e) {
      setReleaseError(e?.response?.data?.detail || 'Could not release this message.')
      setReleaseState('error')
    }
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
      {/* Left: verdict + case */}
      <div className="lg:col-span-1 flex flex-col gap-5">
        <Panel title="Verdict" icon={ShieldCheck}>
          <div className="flex flex-col items-center py-2">
            <RiskGauge score={result.risk_score} decision={result.decision} />
            <p className="mt-4 text-sm font-medium text-slate-200 text-center">
              Classified as <span className="font-mono text-trace">{result.classification}</span>
            </p>
            <p className="mt-1 text-xs text-slate-500 text-center font-mono">{result.subject || '(no subject)'}</p>

            <div className="w-full mt-5 pt-4 border-t border-base-700 space-y-2 text-xs font-mono">
              <div className="flex justify-between"><span className="text-slate-500">Case ID</span><span className="text-slate-200">{result.case_id}</span></div>
              <div className="flex justify-between"><span className="text-slate-500">From</span><span className="text-slate-200 truncate max-w-[160px]">{result.sender?.from_address}</span></div>
              <div className="flex justify-between"><span className="text-slate-500">Evidence SHA-256</span></div>
              <div className="break-all text-slate-400 text-[10px] leading-relaxed">{result.evidence_hash}</div>
            </div>

            {result.decision !== 'ALLOW' && releaseState !== 'released' && (
              <button
                onClick={handleRelease}
                disabled={releaseState === 'loading'}
                className="mt-4 w-full inline-flex items-center justify-center gap-2 rounded-lg border border-base-600 text-slate-300 text-xs font-medium py-2.5 hover:bg-base-800 transition-colors disabled:opacity-60"
              >
                {releaseState === 'loading' ? <Loader2 size={14} className="animate-spin" /> : <Undo2 size={14} />}
                Release from quarantine
              </button>
            )}
            {releaseState === 'released' && (
              <p className="mt-4 text-xs text-signal-safe">Released back to inbox.</p>
            )}
            {releaseError && <p className="mt-2 text-xs text-signal-danger">{releaseError}</p>}

            <div className="mt-4 w-full">
              <LegalReportButtons caseId={result.case_id} />
            </div>

            <Link
              to={`/campaign-graph?caseId=${encodeURIComponent(result.case_id)}`}
              className="mt-2 w-full inline-flex items-center justify-center gap-2 rounded-lg border border-base-600 text-slate-400 text-xs font-medium py-2.5 hover:bg-base-800 transition-colors"
            >
              <Waypoints size={13} /> View in Campaign Graph
            </Link>
          </div>
        </Panel>

        <RecommendationPanel recommendation={result.recommendation} />
        <BlockchainPanel caseId={result.case_id} />
      </div>

      {/* Middle column */}
      <div className="lg:col-span-1 flex flex-col gap-5">
        <Panel title="Risk Fusion Breakdown" icon={GitBranch}>
          <div className="space-y-3.5">
            <ScoreBar label="AI Intent" score={result.ai?.score ?? 0} weight={0.25} />
            <ScoreBar label="Header / Authentication" score={result.forensics?.score ?? 0} weight={0.20} />
            <ScoreBar label="URL Intelligence" score={result.urls?.length ? Math.max(...result.urls.map(u => u.score)) : 0} weight={0.20} />
            <ScoreBar label="Attachment" score={result.attachments?.length ? Math.max(...result.attachments.map(a => a.score)) : 0} weight={0.25} />
          </div>
          <div className="mt-4 pt-3 border-t border-base-700 space-y-1.5">
            {result.explanation?.map((line, i) => (
              <p key={i} className="text-[11px] font-mono text-slate-500 leading-relaxed">→ {line}</p>
            ))}
          </div>
        </Panel>

        <Panel title="AI / NLP Intent Engine" icon={BrainCircuit}>
          <div className="flex items-center gap-2 mb-2">
            <span className="text-xs font-mono px-2 py-0.5 rounded bg-base-700 text-slate-300">
              category: {result.ai?.category}
            </span>
            {result.ai?.model_confidence != null && (
              <span className="text-xs font-mono text-slate-500">confidence {(result.ai.model_confidence * 100).toFixed(0)}%</span>
            )}
          </div>
          <ul className="space-y-1.5">
            {result.ai?.reasons?.map((r, i) => (
              <li key={i} className="text-xs text-slate-400 flex gap-2">
                <AlertTriangle size={13} className="text-signal-watch mt-0.5 shrink-0" />
                {r}
              </li>
            ))}
          </ul>
        </Panel>

        <Panel title="Header Forensics" icon={FileSearch2}>
          <div className="grid grid-cols-3 gap-2 mb-3">
            {['spf', 'dkim', 'dmarc'].map((k) => (
              <div key={k} className="rounded-lg border border-base-700 py-2 text-center">
                <div className="text-[10px] uppercase text-slate-500 font-mono">{k}</div>
                <div className={`text-sm font-semibold font-mono ${authColor(result.authentication?.[k])}`}>
                  {result.authentication?.[k]}
                </div>
              </div>
            ))}
          </div>
          <ul className="space-y-1.5">
            {result.forensics?.anomalies?.map((a, i) => (
              <li key={i} className="text-xs text-slate-400 flex gap-2">
                <AlertTriangle size={13} className="text-signal-danger mt-0.5 shrink-0" /> {a}
              </li>
            ))}
          </ul>
        </Panel>
      </div>

      {/* Right column */}
      <div className="lg:col-span-1 flex flex-col gap-5">
        <Panel title="URL Intelligence" icon={Link2}>
          {result.urls?.length ? (
            <div className="space-y-3">
              {result.urls.map((u, i) => (
                <div key={i} className="text-xs">
                  <p className="font-mono text-slate-300 truncate">{u.original_url}</p>
                  <p className="text-slate-500 mt-0.5">score {u.score}/100 · {u.registered_domain}</p>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-xs text-slate-500 font-mono">No URLs found in message body.</p>
          )}
        </Panel>

        <Panel title="Attachment Scanner" icon={Paperclip}>
          {result.attachments?.length ? (
            <div className="space-y-2.5">
              {result.attachments.map((a, i) => (
                <div key={i} className="text-xs border border-base-700 rounded-lg p-2.5">
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-mono text-slate-300 truncate">{a.filename}</span>
                    <span className={`text-[10px] px-1.5 py-0.5 rounded border font-mono ${sevColor[a.severity]}`}>{a.severity}</span>
                  </div>
                  {a.findings.map((f, j) => <p key={j} className="text-slate-500 leading-relaxed">• {f}</p>)}
                </div>
              ))}
            </div>
          ) : (
            <p className="text-xs text-slate-500 font-mono">No attachments present.</p>
          )}
        </Panel>

        <Panel title="Geolocation (probable origin)" icon={MapPinned}>
          <GeoMap geolocation={result.geolocation} />
          {result.geolocation?.ip && (
            <p className="mt-2 text-[11px] font-mono text-slate-500">
              IP {result.geolocation.ip} · confidence: {result.geolocation.confidence}
            </p>
          )}
        </Panel>
      </div>
    </div>
  )
}
