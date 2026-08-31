function colorForScore(score) {
  if (score >= 75) return '#ff2d55'
  if (score >= 40) return '#f5b942'
  return '#2dd4a7'
}

export default function ScoreBar({ label, score, weight }) {
  const color = colorForScore(score)
  return (
    <div>
      <div className="flex items-baseline justify-between mb-1">
        <span className="text-xs font-medium text-slate-300">{label}</span>
        <span className="text-xs font-mono text-slate-500">
          {score}/100 {weight != null && <span className="text-slate-600">· w{weight}</span>}
        </span>
      </div>
      <div className="h-1.5 rounded-full bg-base-700 overflow-hidden">
        <div
          className="h-full rounded-full"
          style={{ width: `${score}%`, backgroundColor: color, transition: 'width 0.6s ease' }}
        />
      </div>
    </div>
  )
}
