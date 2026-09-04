export default function StatCard({ icon: Icon, label, value, accent = 'trace' }) {
  const accentClasses = {
    trace: 'text-trace bg-trace/10 border-trace/30',
    safe: 'text-signal-safe bg-signal-safe/10 border-signal-safe/30',
    watch: 'text-signal-watch bg-signal-watch/10 border-signal-watch/30',
    danger: 'text-signal-danger bg-signal-danger/10 border-signal-danger/30',
    wire: 'text-wire bg-wire/10 border-wire/30',
  }[accent]

  return (
    <div className="rounded-xl border border-base-700 bg-base-900/60 backdrop-blur-sm p-4 flex items-center gap-3.5">
      <div className={`w-10 h-10 rounded-lg border flex items-center justify-center shrink-0 ${accentClasses}`}>
        <Icon size={18} strokeWidth={2} />
      </div>
      <div className="min-w-0">
        <p className="font-display text-2xl font-semibold text-slate-50 tabular-nums leading-tight">{value}</p>
        <p className="text-xs text-slate-500 truncate">{label}</p>
      </div>
    </div>
  )
}
