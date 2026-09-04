import { Sparkles, Info } from 'lucide-react'
import Panel from './Panel.jsx'

export default function RecommendationPanel({ recommendation }) {
  return (
    <Panel title="AI Recommendation" icon={Sparkles}>
      {recommendation?.recommendation ? (
        <>
          <p className="text-sm text-slate-200 leading-relaxed">{recommendation.recommendation}</p>
          {recommendation.recommendation_engine && (
            <p className="mt-2 text-[11px] font-mono text-slate-500">via {recommendation.recommendation_engine}</p>
          )}
        </>
      ) : (
        <div className="flex items-start gap-2 text-xs text-slate-500">
          <Info size={14} className="mt-0.5 shrink-0" />
          <p>A tailored recommendation isn't available for this case yet.</p>
        </div>
      )}
    </Panel>
  )
}
