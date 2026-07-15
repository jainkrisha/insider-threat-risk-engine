import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Play, Loader2, AlertTriangle, ChevronRight, User } from 'lucide-react'
import GlassCard from '../components/GlassCard'
import TierBadge from '../components/TierBadge'
import SignalBar from '../components/SignalBar'
import AuditBadge from '../components/AuditBadge'
import { scoreUser, DEMO_SCENARIOS, type ScoreResponse } from '../api'

type Step = 'pick' | 'result'

export default function Dashboard() {
  const navigate = useNavigate()

  const [step, setStep]         = useState<Step>('pick')
  const [loading, setLoading]   = useState(false)
  const [error, setError]       = useState<string | null>(null)
  const [result, setResult]     = useState<ScoreResponse | null>(null)
  const [activeScenario, setActiveScenario] = useState<number | null>(null)

  async function runScenario(idx: number) {
    setActiveScenario(idx)
    setError(null)
    setLoading(true)
    try {
      const res = await scoreUser(DEMO_SCENARIOS[idx].payload)
      setResult(res)
      setStep('result')
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Scoring failed')
    } finally {
      setLoading(false)
    }
  }

  const tierGlow = result
    ? result.risk_tier === 'Critical' || result.risk_tier === 'High' ? 'red'
    : 'green'
    : 'none'

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 py-12 space-y-8">

      {/* Header + breadcrumb */}
      <div className="space-y-1">
        <p className="section-label">Analyst Workspace</p>
        <h1 className="text-3xl font-bold">Insider Threat Dashboard</h1>
        {step === 'result' && result && (
          <div className="flex items-center gap-1.5 text-sm text-slate-400 pt-1">
            <button onClick={() => setStep('pick')} className="hover:text-white transition-colors">
              Scenarios
            </button>
            <ChevronRight className="w-3.5 h-3.5" />
            <span className="text-white">{result.user}</span>
          </div>
        )}
      </div>

      {/* ── STEP 1: Scenario Picker ── */}
      {step === 'pick' && (
        <div className="space-y-6 animate-fade-in">
          <p className="text-slate-400">
            Select a scenario below to run a live analysis against the risk engine.
          </p>

          <div className="grid sm:grid-cols-3 gap-5">
            {DEMO_SCENARIOS.map((s, i) => (
              <button
                key={s.label}
                disabled={loading}
                onClick={() => runScenario(i)}
                className={`text-left glass rounded-2xl p-6 border transition-all duration-200 space-y-3 cursor-pointer
                  hover:-translate-y-1 hover:shadow-glow-purple active:translate-y-0
                  ${activeScenario === i && loading
                    ? 'border-indigo-500/50 bg-indigo-500/5'
                    : 'border-white/5 hover:border-indigo-500/30'
                  }`}
              >
                <div className="flex items-center justify-between">
                  <User className="w-5 h-5 text-slate-400" />
                  {activeScenario === i && loading
                    ? <Loader2 className="w-4 h-4 text-indigo-400 animate-spin" />
                    : <ChevronRight className="w-4 h-4 text-slate-600" />
                  }
                </div>
                <div>
                  <p className="font-semibold">{s.label}</p>
                  <p className="text-xs font-mono text-slate-500 mt-0.5">{s.payload.user}</p>
                </div>
                <p className="text-sm text-slate-400 leading-relaxed">{s.description}</p>
                <div>
                  <TierBadge tier={s.tier as never} />
                </div>
              </button>
            ))}
          </div>

          {error && (
            <div className="flex items-center gap-3 bg-red-900/30 border border-red-500/30 rounded-xl p-4 text-red-400 text-sm animate-fade-in">
              <AlertTriangle className="w-4 h-4 shrink-0" />
              {error}
            </div>
          )}
        </div>
      )}

      {/* ── STEP 2: Result ── */}
      {step === 'result' && result && (
        <div className="space-y-6 animate-slide-up">

          {/* Score card */}
          <GlassCard glow={tierGlow as never} className="text-center space-y-4">
            <div>
              <p className="text-sm text-slate-400 uppercase tracking-widest mb-1">Risk Score</p>
              <p className={`text-7xl font-extrabold ${
                result.risk_tier === 'Critical' ? 'text-red-400'
                : result.risk_tier === 'High'   ? 'text-orange-400'
                : result.risk_tier === 'Medium' ? 'text-yellow-400'
                : 'text-emerald-400'
              }`}>
                {result.risk_score.toFixed(1)}
              </p>
              <p className="text-slate-500 text-sm">/ 100</p>
            </div>
            <TierBadge tier={result.risk_tier} />
            <p className="text-sm text-slate-400 font-mono">{result.user} · model v{result.model_version}</p>
          </GlassCard>

          <div className="grid sm:grid-cols-2 gap-5">

            {/* Narrative */}
            <GlassCard className="space-y-3">
              <h2 className="font-semibold text-sm text-slate-300 uppercase tracking-wider">
                Narrative Explanation
              </h2>
              <p className="text-sm text-slate-300 leading-relaxed">{result.narrative_explanation}</p>
            </GlassCard>

            {/* Top signals */}
            <GlassCard className="space-y-3">
              <h2 className="font-semibold text-sm text-slate-300 uppercase tracking-wider">
                Top Anomaly Signals
              </h2>
              {result.top_signals.length > 0
                ? result.top_signals.map(s => <SignalBar key={s.feature} signal={s} />)
                : <p className="text-sm text-slate-500">No significant deviations detected.</p>
              }
            </GlassCard>

          </div>

          {/* Recommended Actions */}
          <GlassCard className="space-y-3">
            <h2 className="font-semibold text-sm text-slate-300 uppercase tracking-wider">
              Recommended Actions
            </h2>
            {result.recommended_actions.length > 0 ? (
              <div className="flex flex-wrap gap-2">
                {result.recommended_actions.map(a => (
                  <span key={a} className="px-3 py-1.5 bg-slate-800 border border-slate-700 rounded-lg text-xs font-mono text-slate-300">
                    {a.replace(/_/g, ' ')}
                  </span>
                ))}
              </div>
            ) : (
              <p className="text-sm text-slate-500">No strict actions required at this risk level.</p>
            )}
          </GlassCard>

          {/* Audit badge */}
          {result.audit_record_id && (
            <AuditBadge
              recordId={result.audit_record_id}
              onViewAudit={() => navigate(`/dashboard/report?user=${result.user}&record=${result.audit_record_id}`)}
            />
          )}

          {/* Full report button */}
          <div className="flex gap-3 flex-wrap">
            <button
              onClick={() => navigate(`/dashboard/report?user=${result.user}&record=${result.audit_record_id ?? ''}`)}
              className="btn-primary flex items-center gap-2"
            >
              <Play className="w-4 h-4" /> View full report
            </button>
            <button
              onClick={() => { setStep('pick'); setActiveScenario(null); setResult(null) }}
              className="btn-ghost border border-white/10"
            >
              ← Back to scenarios
            </button>
          </div>
        </div>
      )}

    </div>
  )
}
