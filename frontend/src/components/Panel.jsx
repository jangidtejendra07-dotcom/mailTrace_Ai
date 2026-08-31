export default function Panel({ title, icon: Icon, right, children, className = '' }) {
  return (
    <div className={`rounded-xl border border-base-700 bg-base-900/60 backdrop-blur-sm ${className}`}>
      {title && (
        <div className="flex items-center justify-between px-4 py-3 border-b border-base-700">
          <div className="flex items-center gap-2">
            {Icon && <Icon size={14} className="text-trace" strokeWidth={2.2} />}
            <h3 className="text-[11px] font-mono uppercase tracking-widest text-slate-400">{title}</h3>
          </div>
          {right}
        </div>
      )}
      <div className="p-4">{children}</div>
    </div>
  )
}
