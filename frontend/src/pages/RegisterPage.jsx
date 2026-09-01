import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Radar, Mail, Lock, User, ArrowRight, Loader2, ShieldAlert } from 'lucide-react'
import { useAuth } from '../context/AuthContext.jsx'
import AuthShell from '../components/AuthShell.jsx'

export default function RegisterPage() {
  const { register } = useAuth()
  const navigate = useNavigate()
  const [fullName, setFullName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  async function handleSubmit(e) {
    e.preventDefault()
    setError(null)
    if (password.length < 8) {
      setError('Password must be at least 8 characters.')
      return
    }
    setLoading(true)
    try {
      await register(email, password, fullName)
      navigate('/inbox?auto_connect=1')
    } catch (err) {
      setError(err?.response?.data?.detail || 'Registration failed.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <AuthShell>
      <div className="flex items-center gap-2.5 mb-8">
        <div className="w-10 h-10 rounded-lg bg-trace/15 border border-trace/40 flex items-center justify-center">
          <Radar size={20} className="text-trace" strokeWidth={2.2} />
        </div>
        <div>
          <div className="font-display font-semibold text-lg text-slate-100 leading-tight">MailTrace AI</div>
          <div className="text-[10px] font-mono uppercase tracking-widest text-trace/80">Analyst Console</div>
        </div>
      </div>

      <h1 className="font-display text-2xl font-semibold text-slate-50 mb-1.5">Create your account</h1>
      <p className="text-sm text-slate-400 mb-8">Set up your analyst console in a few seconds.</p>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="text-xs font-medium text-slate-400 mb-1.5 block">Full name</label>
          <div className="relative">
            <User size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-500" />
            <input
              type="text" value={fullName} onChange={(e) => setFullName(e.target.value)}
              placeholder="Jane Analyst"
              className="w-full bg-base-800 border border-base-600 rounded-lg pl-10 pr-4 py-2.5 text-sm text-slate-100 placeholder:text-slate-600 focus:outline-none focus:ring-2 focus:ring-trace/50 focus:border-trace/50"
            />
          </div>
        </div>
        <div>
          <label className="text-xs font-medium text-slate-400 mb-1.5 block">Email</label>
          <div className="relative">
            <Mail size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-500" />
            <input
              type="email" required value={email} onChange={(e) => setEmail(e.target.value)}
              placeholder="you@company.com"
              className="w-full bg-base-800 border border-base-600 rounded-lg pl-10 pr-4 py-2.5 text-sm text-slate-100 placeholder:text-slate-600 focus:outline-none focus:ring-2 focus:ring-trace/50 focus:border-trace/50"
            />
          </div>
        </div>
        <div>
          <label className="text-xs font-medium text-slate-400 mb-1.5 block">Password</label>
          <div className="relative">
            <Lock size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-500" />
            <input
              type="password" required value={password} onChange={(e) => setPassword(e.target.value)}
              placeholder="At least 8 characters"
              className="w-full bg-base-800 border border-base-600 rounded-lg pl-10 pr-4 py-2.5 text-sm text-slate-100 placeholder:text-slate-600 focus:outline-none focus:ring-2 focus:ring-trace/50 focus:border-trace/50"
            />
          </div>
        </div>

        {error && (
          <div className="flex items-center gap-2 text-xs text-signal-danger bg-signal-danger/10 border border-signal-danger/30 rounded-lg px-3 py-2.5">
            <ShieldAlert size={14} /> {error}
          </div>
        )}

        <button
          type="submit" disabled={loading}
          className="w-full inline-flex items-center justify-center gap-2 rounded-lg bg-trace text-base-950 font-semibold text-sm py-2.5 hover:bg-trace/90 transition-colors disabled:opacity-60"
        >
          {loading ? <Loader2 size={16} className="animate-spin" /> : <>Create account <ArrowRight size={15} /></>}
        </button>
      </form>

      <p className="mt-6 text-center text-sm text-slate-500">
        Already have an account? <Link to="/login" className="text-trace hover:underline font-medium">Sign in</Link>
      </p>
    </AuthShell>
  )
}
