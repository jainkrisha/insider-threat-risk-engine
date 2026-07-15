import { Link } from 'react-router-dom'
import { ShieldCheck, Zap, Brain, Lock, ArrowRight, TrendingUp } from 'lucide-react'
import GlassCard from '../components/GlassCard'

const STATS = [
  { value: '937', label: 'Users analysed' },
  { value: '47/48', label: 'Threats caught (Top-100)' },
  { value: 'F1 0.635', label: 'Model F1 score' },
  { value: 'ML-KEM-768', label: 'Post-quantum encryption' },
]

const HIGHLIGHTS = [
  {
    icon: <Brain className="w-5 h-5 text-indigo-400" />,
    title: 'Hybrid AI Engine',
    body: 'Isolation Forest + Random Forest ensemble catches both sudden spikes and slow-burn exfiltration.',
  },
  {
    icon: <Zap className="w-5 h-5 text-emerald-400" />,
    title: 'Explainable Results',
    body: 'Every flag comes with a plain-English explanation of exactly which behaviour deviated and by how much.',
  },
  {
    icon: <Lock className="w-5 h-5 text-indigo-400" />,
    title: 'Quantum-Safe Vault',
    body: 'High-risk audit records are sealed with hybrid X25519 + ML-KEM-768 encryption before storage.',
  },
  {
    icon: <TrendingUp className="w-5 h-5 text-yellow-400" />,
    title: 'Real-Time Scoring',
    body: "The FastAPI backend scores a user's activity in milliseconds \u2014 built for live SOC workflows.",
  },
]

export default function Home() {
  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-16 space-y-24">

      {/* ── Hero ── */}
      <section className="text-center space-y-6 animate-fade-in">
        <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full glass border border-indigo-500/25 text-indigo-400 text-sm">
          <ShieldCheck className="w-4 h-4" />
          FinSpark · Insider Threat Detection
        </div>

        <h1 className="text-5xl sm:text-6xl lg:text-7xl font-extrabold leading-tight tracking-tight">
          Catch insider threats{' '}
          <span className="gradient-text">before the damage is done</span>
        </h1>

        <p className="max-w-2xl mx-auto text-lg text-slate-400 leading-relaxed">
          FinSpark continuously monitors employee behaviour and flags anomalies — unusual
          login patterns, off-hours activity, mass data transfers — using an ensemble of
          AI models trained on the CERT r4.2 insider threat dataset.
        </p>

        <div className="flex flex-wrap justify-center gap-4">
          <Link to="/dashboard" className="btn-primary flex items-center gap-2 text-base">
            Investigate flagged users <ArrowRight className="w-4 h-4" />
          </Link>
          <Link to="/about" className="btn-ghost border border-white/10 text-base">
            How it works
          </Link>
        </div>
      </section>

      {/* ── Stats strip ── */}
      <section className="grid grid-cols-2 sm:grid-cols-4 gap-4 animate-slide-up">
        {STATS.map(s => (
          <GlassCard key={s.label} className="text-center py-6">
            <p className="text-2xl sm:text-3xl font-bold gradient-text">{s.value}</p>
            <p className="text-xs text-slate-400 mt-1">{s.label}</p>
          </GlassCard>
        ))}
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
              <div className="w-10 h-10 rounded-xl bg-slate-800 flex items-center justify-center">
                {h.icon}
              </div>
              <h3 className="font-semibold text-white">{h.title}</h3>
              <p className="text-sm text-slate-400 leading-relaxed">{h.body}</p>
            </GlassCard>
          ))}
        </div>
      </section>

      {/* ── CTA banner ── */}
      <section className="relative overflow-hidden rounded-3xl glass border border-purple-500/20 p-10 text-center space-y-5 shadow-glow-purple animate-slide-up">
        <div className="absolute inset-0 bg-gradient-to-br from-indigo-500/5 to-cyan-500/5 pointer-events-none" />
        <h2 className="text-3xl font-bold relative z-10">Ready to run an analysis?</h2>
        <p className="text-slate-400 relative z-10">
          Pick a demo scenario or enter a user ID and get a full risk verdict in seconds.
        </p>
        <div className="flex flex-wrap justify-center gap-4 relative z-10">
          <Link to="/dashboard" className="btn-primary inline-flex items-center gap-2">
            Open Dashboard <ArrowRight className="w-4 h-4" />
          </Link>
          <Link to="/live-demo" className="btn-ghost border border-white/10 inline-flex items-center gap-2 px-6 py-3">
            Live Demo <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </section>

    </div>
  )
}
