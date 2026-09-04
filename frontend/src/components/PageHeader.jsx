export default function PageHeader({ icon: Icon, iconClassName = 'text-trace', title, subtitle, right }) {
  return (
    <header className="mb-8 flex items-start justify-between gap-4">
      <div className="flex items-center gap-3">
        {Icon && <Icon className={iconClassName} size={22} />}
        <div>
          <h1 className="font-display text-2xl font-semibold text-slate-50">{title}</h1>
          {subtitle && <p className="text-sm text-slate-400 mt-0.5 max-w-2xl">{subtitle}</p>}
        </div>
      </div>
      {right}
    </header>
  )
}
