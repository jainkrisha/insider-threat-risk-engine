import { Link } from 'react-router-dom'
import { ShieldCheck, Zap, Brain, Lock, ArrowRight, TrendingUp } from 'lucide-react'
import GlassCard from '../components/GlassCard'

const HIGHLIGHTS = [
  {
    icon: <Brain className="w-5 h-5 text-[#496b52]" />,
    title: 'Hybrid AI Engine',
    body: 'Isolation Forest + Random Forest ensemble catches both sudden spikes and slow-burn exfiltration.',
  },
  {
    icon: <Zap className="w-5 h-5 text-[#496b52]" />,
    title: 'Explainable Results',
    body: 'Every flag comes with a plain-English explanation of exactly which behaviour deviated and by how much.',
  },
  {
    icon: <Lock className="w-5 h-5 text-[#496b52]" />,
    title: 'Quantum-Safe Vault',
    body: 'High-risk audit records are sealed with hybrid X25519 + ML-KEM-768 encryption before storage.',
  },
  {
    icon: <TrendingUp className="w-5 h-5 text-[#92402d]" />,
    title: 'Real-Time Scoring',
    body: "The FastAPI backend scores a user's activity in milliseconds — built for live SOC workflows.",
  },
]

// --- SOC Charts ---
const TREND_DATA = [
  { day: 'Mon', score: 12 },
  { day: 'Tue', score: 15 },
  { day: 'Wed', score: 14 },
  { day: 'Thu', score: 18 },
  { day: 'Fri', score: 82 }, // Spike!
  { day: 'Sat', score: 85 },
  { day: 'Sun', score: 80 },
]

function HomeLineChart() {
  const points = TREND_DATA.map((d, i) => {
    const x = (i / (TREND_DATA.length - 1)) * 100;
    const y = 100 - d.score;
    return `${x},${y}`;
  }).join(' ');

  return (
    <div className="h-40 relative w-full pt-4 mb-4 flex gap-2">
      {/* Y-Axis */}
      <div className="w-6 relative text-[10px] text-[#716a5d] h-full font-medium">
        <span className="absolute top-0 right-0 transform -translate-y-1/2">100</span>
        <span className="absolute top-1/4 right-0 transform -translate-y-1/2">75</span>
        <span className="absolute top-2/4 right-0 transform -translate-y-1/2">50</span>
        <span className="absolute top-3/4 right-0 transform -translate-y-1/2">25</span>
        <span className="absolute top-full right-0 transform -translate-y-1/2">0</span>
      </div>

      {/* Graph Area */}
      <div className="flex-1 relative h-full border-b border-[#a39882]">
        <svg className="w-full h-full overflow-visible" viewBox="0 0 100 100" preserveAspectRatio="none">
          <line x1="0" y1="25" x2="100" y2="25" stroke="#cab593" strokeDasharray="2" strokeWidth="0.5" />
          <line x1="0" y1="50" x2="100" y2="50" stroke="#cab593" strokeDasharray="2" strokeWidth="0.5" />
          <line x1="0" y1="75" x2="100" y2="75" stroke="#cab593" strokeDasharray="2" strokeWidth="0.5" />
          <polyline points={points} fill="none" stroke="#92402d" strokeWidth="2" vectorEffect="non-scaling-stroke" />
        </svg>
        {TREND_DATA.map((d, i) => {
          const left = `${(i / (TREND_DATA.length - 1)) * 100}%`;
          const top = `${100 - d.score}%`;
          const isFlagged = d.score > 70;
          const size = isFlagged ? 12 : 8;
          const bg = isFlagged ? 'bg-[#92402d]' : 'bg-[#496b52]';
          return (
            <div
              key={i}
              className={`absolute rounded-full border-2 border-[#e8dfcd] ${bg} transform -translate-x-1/2 -translate-y-1/2`}
              style={{ left, top, width: size, height: size }}
            />
          )
        })}
        {/* X-Axis Labels */}
        <div className="absolute left-0 right-0 -bottom-6 flex justify-between">
          {TREND_DATA.map((d, i) => (
            <span key={i} className={`text-[10px] ${d.score > 70 ? 'text-[#92402d] font-bold' : 'text-[#716a5d]'}`}>{d.day}</span>
          ))}
        </div>
      </div>
    </div>
  )
}

const TOP_SIGNALS = [
  { label: 'Off-hours Logins', count: 420 },
  { label: 'Removable Media', count: 315 },
  { label: 'External Emails', count: 280 },
  { label: 'Suspicious URLs', count: 195 },
  { label: 'Unusual PC Access', count: 120 },
]

function HomeBarChart() {
  const max = TOP_SIGNALS[0].count
  return (
    <div className="flex flex-col justify-center h-48 gap-3 pt-2">
      {TOP_SIGNALS.map(s => {
        const w = (s.count / max) * 100
        return (
          <div key={s.label} className="space-y-1">
            <div className="flex justify-between text-xs">
              <span className="text-[#26201b] font-medium">{s.label}</span>
              <span className="text-[#716a5d]">{s.count}</span>
            </div>
            <div className="w-full bg-[#e5dfd3] rounded-full h-2">
              <div className="bg-[#496b52] h-2 rounded-full" style={{ width: `${w}%` }} />
            </div>
          </div>
        )
      })}
    </div>
  )
}

function HomeHeatmap() {
  const days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
  const getIntensity = (d: number, h: number) => {
    if (d < 5 && h >= 9 && h <= 17) return Math.random() * 0.5 + 0.3
    if (d === 4 && h >= 21 && h <= 23) return Math.random() * 0.4 + 0.6
    if (d === 5 && h >= 0 && h <= 3) return Math.random() * 0.4 + 0.6
    return Math.random() * 0.1
  }

  return (
    <div className="pt-2 flex flex-col gap-1 h-48 justify-center">
      {days.map((day, d) => (
        <div key={day} className="flex items-center gap-2">
          <span className="text-[10px] text-[#716a5d] w-6">{day}</span>
          <div className="flex-1 flex gap-0.5">
            {Array.from({ length: 24 }).map((_, h) => {
              const val = getIntensity(d, h)
              let bg = 'bg-[#e5dfd3]' 
              if (val > 0.1) bg = 'bg-[#496b52]/30'
              if (val > 0.4) bg = 'bg-[#496b52]/60'
              if (val > 0.7) bg = 'bg-[#92402d]' 
              return (
                <div key={h} className={`flex-1 h-3 rounded-sm ${bg}`} title={`${h}:00`} />
              )
            })}
          </div>
        </div>
      ))}
      <div className="flex items-center gap-2 mt-1">
        <span className="w-6" />
        <div className="flex-1 flex justify-between text-[8px] text-[#716a5d]">
          <span>00:00</span>
          <span>12:00</span>
          <span>23:00</span>
        </div>
      </div>
    </div>
  )
}

export default function Home() {
  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-16 space-y-24">

      {/* ── Hero ── */}
      <section className="text-center space-y-6 animate-fade-in">
        <div className="inline-flex items-center gap-2 px-6 py-2.5 rounded-full glass border border-[#496b52]/25 text-[#496b52] text-base font-semibold shadow-sm">
          <ShieldCheck className="w-5 h-5" />
          Vigil · Insider Threat Detection
        </div>

        <h1 className="text-5xl sm:text-6xl lg:text-7xl font-extrabold leading-tight tracking-tight">
          Catch insider threats{' '}
          <span className="gradient-text">before the damage is done</span>
        </h1>

        <p className="max-w-2xl mx-auto text-lg text-[#26201b] leading-relaxed">
          Vigil continuously monitors employee behaviour and flags anomalies — unusual
          login patterns, off-hours activity, mass data transfers — using an ensemble of
          AI models trained on the CERT r4.2 insider threat dataset.
        </p>

        <div className="flex flex-wrap justify-center gap-4">
          <Link to="/dashboard" className="btn-primary flex items-center gap-2 text-base">
            Investigate flagged users <ArrowRight className="w-4 h-4" />
          </Link>
          <Link to="/about" className="btn-ghost border border-[#a39882] text-base">
            How it works
          </Link>
        </div>
      </section>

      
      {/* ── SOC Dashboards ── */}
      <section className="space-y-8 animate-slide-up">
        <div className="text-center space-y-2 mb-8">
          <p className="section-label">SOC Analyst View</p>
          <h2 className="text-3xl font-bold">See the full context of every alert</h2>
        </div>
        
        <div className="grid grid-cols-1 gap-6">
          <GlassCard className="p-6 flex flex-col justify-between">
            <div className="mb-4">
              <h3 className="font-semibold text-[#26201b]">Portfolio Risk Trend</h3>
              <p className="text-xs text-[#716a5d]">Aggregate peak risk score (7-day history)</p>
            </div>
            <HomeLineChart />
          </GlassCard>

          <GlassCard className="p-6 flex flex-col justify-between">
            <div className="mb-4">
              <h3 className="font-semibold text-[#26201b]">Top Anomalies</h3>
              <p className="text-xs text-[#716a5d]">Portfolio-wide drivers (this week)</p>
            </div>
            <HomeBarChart />
          </GlassCard>

          <GlassCard className="p-6 flex flex-col justify-between">
            <div className="mb-4">
              <h3 className="font-semibold text-[#26201b]">Global Activity Heatmap</h3>
              <p className="text-xs text-[#716a5d]">Company-wide logins (Off-hours anomaly)</p>
            </div>
            <HomeHeatmap />
          </GlassCard>
        </div>
      </section>

      {/* ── Feature highlights ── */}
      <section className="space-y-8 animate-slide-up">
        <div className="text-center space-y-2">
          <p className="section-label">Capabilities</p>
          <h2 className="text-3xl font-bold">Everything a SOC analyst needs</h2>
        </div>

        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6">
          {HIGHLIGHTS.map(h => (
            <GlassCard key={h.title} className="glass-hover space-y-3">
              <div className="w-10 h-10 rounded-xl bg-[#e8dfcd] flex items-center justify-center">
                {h.icon}
              </div>
              <h3 className="font-semibold text-[#26201b]">{h.title}</h3>
              <p className="text-sm text-[#26201b] leading-relaxed">{h.body}</p>
            </GlassCard>
          ))}
        </div>
      </section>

      {/* ── CTA banner ── */}
      <section className="relative overflow-hidden rounded-3xl glass border border-[#92402d]/20 p-10 text-center space-y-5 shadow-glow-teal animate-slide-up">
        <div className="absolute inset-0 bg-gradient-to-br from-[#496b52]/5 to-[#92402d]/5 pointer-events-none" />
        <h2 className="text-3xl font-bold relative z-10">Ready to run an analysis?</h2>
        <p className="text-[#26201b] relative z-10">
          Pick a demo scenario or enter a user ID and get a full risk verdict in seconds.
        </p>
        <div className="flex flex-wrap justify-center gap-4 relative z-10">
          <Link to="/dashboard" className="btn-primary inline-flex items-center gap-2">
            Dashboard <ArrowRight className="w-4 h-4" />
          </Link>
          <Link to="/about" className="btn-ghost border border-[#a39882] inline-flex items-center gap-2 px-6 py-3">
            How it works <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </section>

    </div>
  )
}
