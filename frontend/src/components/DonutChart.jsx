export default function DonutChart({ segments }) {
  // segments: [{ label, value, color }]
  const total = segments.reduce((sum, s) => sum + s.value, 0)
  const radius = 52
  const strokeWidth = 18
  const circumference = 2 * Math.PI * radius

  let offsetAccum = 0

  return (
    <div className="flex items-center gap-6">
      <svg width="140" height="140" viewBox="0 0 140 140" className="-rotate-90 shrink-0">
        {total === 0 ? (
          <circle cx="70" cy="70" r={radius} fill="none" stroke="#1a232e" strokeWidth={strokeWidth} />
        ) : (
          segments.map((s, i) => {
            const fraction = s.value / total
            const dash = fraction * circumference
            const gap = circumference - dash
            const el = (
              <circle
                key={i}
                cx="70"
                cy="70"
                r={radius}
                fill="none"
                stroke={s.color}
                strokeWidth={strokeWidth}
                strokeDasharray={`${dash} ${gap}`}
                strokeDashoffset={-offsetAccum}
                strokeLinecap={segments.filter((x) => x.value > 0).length === 1 ? 'butt' : 'round'}
              />
            )
            offsetAccum += dash
            return el
          })
        )}
      </svg>
      <div className="space-y-2 min-w-0">
        {segments.map((s, i) => (
          <div key={i} className="flex items-center gap-2 text-sm">
            <span className="w-2.5 h-2.5 rounded-full shrink-0" style={{ backgroundColor: s.color }} />
            <span className="text-slate-300">{s.label}</span>
            <span className="text-slate-500 font-mono text-xs ml-auto pl-3">{s.value}</span>
          </div>
        ))}
        {total === 0 && <p className="text-xs text-slate-500">No analyzed emails yet.</p>}
      </div>
    </div>
  )
}
