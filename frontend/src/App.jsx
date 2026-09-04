import { Routes, Route, Navigate, NavLink } from 'react-router-dom'
import { LayoutDashboard, FolderClock, ShieldAlert, Waypoints, Settings as SettingsIcon, LogOut, Loader2, Radar } from 'lucide-react'
import { AuthProvider, useAuth } from './context/AuthContext.jsx'
import LoginPage from './pages/LoginPage.jsx'
import RegisterPage from './pages/RegisterPage.jsx'
import DashboardPage from './pages/DashboardPage.jsx'
import CasesPage from './pages/CasesPage.jsx'
import CaseDetailPage from './pages/CaseDetailPage.jsx'
import QuarantinePage from './pages/QuarantinePage.jsx'
import CampaignGraphPage from './pages/CampaignGraphPage.jsx'
import SettingsPage from './pages/SettingsPage.jsx'

function NavItem({ to, icon: Icon, label, end }) {
  return (
    <NavLink
      to={to}
      end={end}
      className={({ isActive }) =>
        `flex items-center gap-2.5 px-3.5 py-2.5 rounded-lg text-sm font-medium transition-colors ${
          isActive
            ? 'bg-trace/10 text-trace border border-trace/30'
            : 'text-slate-400 border border-transparent hover:text-slate-200 hover:bg-base-800'
        }`
      }
    >
      <Icon size={16} strokeWidth={2} />
      {label}
    </NavLink>
  )
}

function AppShell() {
  const { user, logout } = useAuth()

  return (
    <div className="min-h-screen flex">
      <aside className="w-60 shrink-0 border-r border-base-700 bg-base-900/70 backdrop-blur-sm flex flex-col">
        <div className="px-5 py-6 border-b border-base-700">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-md bg-trace/15 border border-trace/40 flex items-center justify-center animate-pulse-ring">
              <Radar size={17} className="text-trace" strokeWidth={2.2} />
            </div>
            <div>
              <div className="font-display font-semibold text-slate-100 leading-tight tracking-tight">MailTrace</div>
              <div className="text-[10px] font-mono uppercase tracking-widest text-trace/80 leading-tight">AI · SIH 26106</div>
            </div>
          </div>
        </div>
        <nav className="flex flex-col gap-1 px-3 py-4">
          <NavItem to="/" end icon={LayoutDashboard} label="Dashboard" />
          <NavItem to="/cases" icon={FolderClock} label="Cases" />
          <NavItem to="/quarantine" icon={ShieldAlert} label="Quarantine" />
          <NavItem to="/campaign-graph" icon={Waypoints} label="Campaign Graph" />
          <NavItem to="/settings" icon={SettingsIcon} label="Settings" />
        </nav>
        <div className="mt-auto px-4 py-4 border-t border-base-700">
          <div className="mb-3">
            <p className="text-xs font-medium text-slate-300 truncate">{user?.full_name || user?.email}</p>
            <p className="text-[11px] text-slate-500 truncate font-mono">{user?.email}</p>
          </div>
          <button
            onClick={logout}
            className="w-full inline-flex items-center gap-2 text-xs font-medium text-slate-500 hover:text-signal-danger transition-colors px-1 py-1"
          >
            <LogOut size={13} /> Sign out
          </button>
        </div>
      </aside>

      <main className="flex-1 min-w-0">
        <Routes>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/cases" element={<CasesPage />} />
          <Route path="/cases/:caseId" element={<CaseDetailPage />} />
          <Route path="/quarantine" element={<QuarantinePage />} />
          <Route path="/campaign-graph" element={<CampaignGraphPage />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </div>
  )
}

function AppRoutes() {
  const { user, loading } = useAuth()

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center text-slate-500 gap-2 text-sm font-mono">
        <Loader2 className="animate-spin" size={18} /> Loading MailTrace…
      </div>
    )
  }

  if (!user) {
    return (
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    )
  }

  return (
    <Routes>
      <Route path="/login" element={<Navigate to="/" replace />} />
      <Route path="/register" element={<Navigate to="/" replace />} />
      <Route path="/*" element={<AppShell />} />
    </Routes>
  )
}

export default function App() {
  return (
    <AuthProvider>
      <AppRoutes />
    </AuthProvider>
  )
}
