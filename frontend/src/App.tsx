import { BrowserRouter, Routes, Route } from 'react-router-dom'
import NavBar    from './components/NavBar'
import Home      from './pages/Home'
import About     from './pages/About'
import Features  from './pages/Features'
import Dashboard from './pages/Dashboard'
import Report    from './pages/Report'
import LiveDemo  from './pages/LiveDemo'

export default function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen flex flex-col">
        <NavBar />
        <main className="flex-1">
          <Routes>
            <Route path="/"                  element={<Home />}      />
            <Route path="/about"             element={<About />}     />
            <Route path="/features"          element={<Features />}  />
            <Route path="/dashboard"         element={<Dashboard />} />
            <Route path="/dashboard/report"  element={<Report />}    />
            <Route path="/live-demo"         element={<LiveDemo />}  />
          </Routes>
        </main>

        {/* Footer */}
        <footer className="border-t border-white/5 py-6 mt-12">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-slate-500">
            <span>FinSpark Risk Engine · FinSpark Hackathon Prototype</span>
            <span>
              Encrypted with ML-KEM-768 + X25519 ·{' '}
              <a
                href="https://github.com/jainkrisha/insider-threat-risk-engine"
                target="_blank"
                rel="noreferrer"
                className="hover:text-slate-300 transition-colors"
              >
                GitHub ↗
              </a>
            </span>
          </div>
        </footer>
      </div>
    </BrowserRouter>
  )
}
