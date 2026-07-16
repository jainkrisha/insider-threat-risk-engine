import { useState, useEffect } from 'react'
import { Link, NavLink, useLocation } from 'react-router-dom'
import { ShieldCheck, Menu, X, Activity, Zap } from 'lucide-react'
import { checkHealth } from '../api'

const NAV_LINKS = [
  { to: '/',          label: 'Home' },
  { to: '/about',     label: 'About' },
  { to: '/features',  label: 'Features' },
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
    <header className="sticky top-0 z-50 bg-[#dfd2bc] border-b border-[#cab593]">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">

        {/* Logo */}
        <Link to="/" className="flex items-center gap-2 font-bold text-xl shrink-0">
          <ShieldCheck className="w-6 h-6 text-[#496b52]" />
          <span className="gradient-text">Vigil</span>
        </Link>

        {/* Desktop Nav */}
        <nav className="hidden md:flex items-center gap-1">
          {NAV_LINKS.map(({ to, label }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              className={({ isActive }) => `text-base font-medium transition-colors px-4 py-2 rounded-md ${
                isActive ? 'text-[#496b52] bg-[#496b52]/10' : 'text-[#26201b] hover:text-[#26201b] hover:bg-[#cab593]/50'
              }`}
            >
              {label}
            </NavLink>
          ))}
        </nav>

        {/* Right: API status + Live Demo CTA */}
        <div className="flex items-center gap-3 shrink-0">
          {/* API health pill */}
          <span
            title={healthy === null ? 'Checking API…' : healthy ? 'Backend healthy — model loaded' : 'Backend offline'}
            className={`hidden sm:flex items-center gap-1.5 text-sm px-3 py-1.5 rounded-full border ${
              healthy === null
                ? 'border-slate-600 text-[#26201b]'
                : healthy
                ? 'border-[#496b52]/40 text-[#496b52] bg-[#496b52]/10'
                : 'border-red-500/40 text-[#92402d] bg-[#92402d]/10'
            }`}
          >
            <Activity className="w-3 h-3" />
            {healthy === null ? 'Checking…' : healthy ? 'API live' : 'API offline'}
          </span>

          {/* Launch App — primary CTA */}
          <Link
            to="/dashboard"
            className="btn-primary text-base py-2.5 px-5 hidden md:flex items-center gap-1.5"
          >
            <Zap className="w-3.5 h-3.5" />
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
        <div className="md:hidden bg-[#dfd2bc] border-b border-[#cab593] px-4 py-4 flex flex-col gap-1 animate-fade-in absolute w-full left-0 top-16 shadow-lg">
          {NAV_LINKS.map(({ to, label }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              className={({ isActive }) =>
                isActive
                  ? 'px-4 py-3 rounded-lg text-[#496b52] bg-[#496b52]/10 font-medium text-lg'
                  : 'px-4 py-3 rounded-lg text-[#26201b] hover:text-[#26201b] hover:bg-[#cab593]/50 transition-colors text-lg'
              }
            >
              {label}
            </NavLink>
          ))}
          <Link to="/dashboard" className="btn-primary text-base py-3 mt-2 text-center flex items-center justify-center gap-2">
            <Zap className="w-3.5 h-3.5" /> Dashboard
          </Link>
        </div>
      )}
    </header>
  )
}
