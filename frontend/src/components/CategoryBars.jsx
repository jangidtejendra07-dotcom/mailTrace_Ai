export default function CategoryBars({ items }) {
  // items: [{ label, value, color }]
  const max = Math.max(1, ...items.map((i) => i.value))

  return (
    <div className="space-y-3.5">
      {items.map((item, i) => (
        <div key={i}>
          <div className="flex items-baseline justify-between mb-1">
            <span className="text-xs font-medium text-slate-300">{item.label}</span>
            <span className="text-xs font-mono text-slate-500">{item.value}</span>
          </div>
          <div className="h-2 rounded-full bg-base-700 overflow-hidden">
            <div
              className="h-full rounded-full"
              style={{
                width: `${(item.value / max) * 100}%`,
                backgroundColor: item.color,
                transition: 'width 0.6s ease',
              }}
            />
          </div>
        </div>
      ))}
      {items.every((i) => i.value === 0) && (
        <p className="text-xs text-slate-500">No threats classified yet.</p>
      )}
    </div>
  )
}
