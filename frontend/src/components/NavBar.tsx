import { useState, useEffect } from 'react'
import { Link, NavLink, useLocation } from 'react-router-dom'
import { ShieldCheck, Menu, X, Activity } from 'lucide-react'
import { checkHealth } from '../api'

const NAV_LINKS = [
  { to: '/',         label: 'Home' },
  { to: '/about',    label: 'About' },
  { to: '/features', label: 'Features' },
]

export default function NavBar() {
  const [open, setOpen]       = useState(false)
  const [healthy, setHealthy] = useState<boolean | null>(null)
  const location              = useLocation()

  useEffect(() => { setOpen(false) }, [location])

  useEffect(() => {
    checkHealth()
      .then(d => setHealthy(d.status === 'healthy' && d.model_loaded))
      .catch(() => setHealthy(false))
  }, [])

  return (
    <header className="sticky top-0 z-50 glass border-b border-white/5">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">

        {/* Logo */}
        <Link to="/" className="flex items-center gap-2 font-bold text-lg">
          <ShieldCheck className="w-6 h-6 text-indigo-400" />
          <span className="gradient-text">FinSpark</span>
          <span className="hidden sm:inline text-slate-400 font-normal text-sm">Risk Engine</span>
        </Link>

        {/* Desktop Nav */}
        <nav className="hidden md:flex items-center gap-1">
          {NAV_LINKS.map(({ to, label }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              className={({ isActive }) => `text-sm font-medium transition-colors px-3 py-1.5 rounded-md ${
                isActive ? 'text-indigo-400 bg-indigo-500/10' : 'text-slate-300 hover:text-white hover:bg-white/5'
              }`}
            >
              {label}
            </NavLink>
          ))}
        </nav>

        {/* Right: health + Dashboard CTA */}
        <div className="flex items-center gap-3">
          {/* API health pill */}
          <span
            title={healthy === null ? 'Checking API…' : healthy ? 'Backend healthy' : 'Backend offline'}
            className={`hidden sm:flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-full border ${
              healthy === null
                ? 'border-slate-600 text-slate-500'
                : healthy
                ? 'border-emerald-500/40 text-emerald-400 bg-emerald-500/10'
                : 'border-red-500/40 text-red-400 bg-red-500/10'
            }`}
          >
            <Activity className="w-3 h-3" />
            {healthy === null ? 'Checking…' : healthy ? 'API live' : 'API offline'}
          </span>

          <Link to="/dashboard" className="btn-primary text-sm py-2 px-4 hidden md:flex">
            Dashboard
          </Link>

          {/* Mobile hamburger */}
          <button className="md:hidden p-2" onClick={() => setOpen(v => !v)}>
            {open ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        </div>
      </div>

      {/* Mobile drawer */}
      {open && (
        <div className="md:hidden glass border-t border-white/5 px-4 py-4 flex flex-col gap-1 animate-fade-in">
          {NAV_LINKS.map(({ to, label }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              className={({ isActive }) =>
                isActive
                  ? 'px-4 py-2.5 rounded-lg text-indigo-400 bg-indigo-500/10 font-medium'
                  : 'px-4 py-2.5 rounded-lg text-slate-300 hover:text-white hover:bg-white/5 transition-colors'
              }
            >
              {label}
            </NavLink>
          ))}
          <Link to="/dashboard" className="btn-primary text-sm mt-2 text-center">
            Open Dashboard
          </Link>
        </div>
      )}
    </header>
  )
}
