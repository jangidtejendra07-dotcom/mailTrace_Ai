const decisionColor = {
  ALLOW: '#2dd4a7',
  QUARANTINE: '#f5b942',
  BLOCK: '#ff2d55',
}

export default function RiskGauge({ score = 0, decision = 'ALLOW' }) {
  const color = decisionColor[decision] || '#2dd4a7'
  const radius = 70
  const circumference = 2 * Math.PI * radius
  const offset = circumference - (score / 100) * circumference

  return (
    <div className="relative flex items-center justify-center">
      <svg width="180" height="180" viewBox="0 0 180 180" className="-rotate-90">
        <circle cx="90" cy="90" r={radius} fill="none" stroke="#1a232e" strokeWidth="14" />
        <circle
          cx="90" cy="90" r={radius} fill="none"
          stroke={color} strokeWidth="14" strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          style={{ transition: 'stroke-dashoffset 0.8s ease, stroke 0.4s ease' }}
        />
      </svg>
      <div className="absolute flex flex-col items-center">
        <span className="font-display text-4xl font-bold text-slate-50 tabular-nums">{score}</span>
        <span className="text-[10px] font-mono uppercase tracking-widest text-slate-500">/ 100 risk</span>
        <span
          className="mt-2 px-2.5 py-0.5 rounded-full text-[11px] font-mono font-semibold tracking-wide"
          style={{ color, backgroundColor: `${color}1a`, border: `1px solid ${color}55` }}
        >
          {decision}
        </span>
      </div>
    </div>
  )
}
