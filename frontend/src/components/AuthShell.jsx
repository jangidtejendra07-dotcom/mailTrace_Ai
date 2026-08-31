import { ShieldCheck, Fingerprint, Network } from 'lucide-react'

export default function AuthShell({ children }) {
  return (
    <div className="min-h-screen flex">
      {/* Left: form */}
      <div className="w-full lg:w-[440px] shrink-0 flex items-center justify-center px-8 py-12 border-r border-base-700">
        <div className="w-full max-w-sm">{children}</div>
      </div>

      {/* Right: brand / visual panel */}
      <div className="hidden lg:flex flex-1 relative overflow-hidden items-center justify-center bg-base-900">
        <div className="absolute inset-0 opacity-40" style={{
          backgroundImage: 'radial-gradient(circle at 30% 20%, rgba(61,220,151,0.15), transparent 45%), radial-gradient(circle at 80% 80%, rgba(124,156,255,0.12), transparent 45%)'
        }} />
        <div className="relative z-10 max-w-md px-10">
          <p className="text-[11px] font-mono uppercase tracking-widest text-trace mb-4">SIH 26106 · Live Deployment</p>
          <h2 className="font-display text-3xl font-semibold text-slate-50 leading-tight mb-6">
            One console for every inbox threat, fully traced.
          </h2>
          <div className="space-y-5">
            <Feature icon={Network} title="Connect Gmail directly" desc="Live inbox sync — no manual file exports, no waiting." />
            <Feature icon={ShieldCheck} title="Explainable risk fusion" desc="Every ALLOW / QUARANTINE / BLOCK comes with the exact reasoning behind it." />
            <Feature icon={Fingerprint} title="Forensic-grade evidence" desc="SHA-256 hashed evidence packages, ready for analyst review." />
          </div>
        </div>
      </div>
    </div>
  )
}

function Feature({ icon: Icon, title, desc }) {
  return (
    <div className="flex gap-3.5">
      <div className="w-9 h-9 shrink-0 rounded-lg bg-trace/10 border border-trace/30 flex items-center justify-center">
        <Icon size={16} className="text-trace" strokeWidth={2} />
      </div>
      <div>
        <p className="text-sm font-medium text-slate-200">{title}</p>
        <p className="text-xs text-slate-500 mt-0.5">{desc}</p>
      </div>
    </div>
  )
}
