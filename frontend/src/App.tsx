import { BrowserRouter, Routes, Route } from 'react-router-dom'
import NavBar    from './components/NavBar'
import Home      from './pages/Home'
import About     from './pages/About'
import Features  from './pages/Features'
import Dashboard from './pages/Dashboard'
import Report    from './pages/Report'

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
          </Routes>
        </main>

        {/* Footer */}
        <footer className="border-t border-[#cab593] py-6 mt-12">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-[#26201b]">
            <span>Vigil Risk Engine · Vigil Hackathon Prototype</span>
            <span>
              Encrypted with ML-KEM-768 + X25519 ·{' '}
              <a
                href="https://github.com/jainkrisha/insider-threat-risk-engine"
                target="_blank"
                rel="noreferrer"
                className="hover:text-[#26201b] transition-colors"
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
