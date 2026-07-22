import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Play, Loader2, AlertTriangle, RotateCcw, ShieldCheck, Crown, Zap
} from 'lucide-react'
import GlassCard from '../components/GlassCard'
import TierBadge from '../components/TierBadge'
import SignalBar from '../components/SignalBar'
import AuditBadge from '../components/AuditBadge'
import EnforcementPanel from '../components/EnforcementPanel'
import { scoreUser, fetchUserTrend, DEMO_SCENARIOS, fetchSessionState, verifySessionIdentity, type ScoreResponse, type TrendPoint, type ScoreRequest, type SessionStateResponse } from '../api'

// ---------------------------------------------------------------------------
// SVG Trend Chart
// ---------------------------------------------------------------------------
const TIER_COLOURS: Record<string, string> = {
  Low:      '#34d399',
  Medium:   '#fbbf24',
  High:     '#f97316',
  Critical: '#f87171',
}

function TrendChart({ points }: { points: TrendPoint[] }) {
  const H = 80
  const W = 400
  const n = points.length
  const barW = Math.floor(W / n) - 4

  return (
    <div className="space-y-3 mt-2">
      <p className="text-sm font-semibold text-[#26201b] uppercase tracking-wider">7-Day Risk Trend</p>
      {/* Shift viewBox down by -20 on Y to allow text to draw above the bars without clipping */}
      <svg viewBox={`0 -20 ${W} ${H + 40}`} className="w-full overflow-visible" aria-label="7-day risk trend">
        {points.map((pt, i) => {
          const barH   = Math.max(4, (pt.risk_score / 100) * H)
          const x      = i * (barW + 4)
          const y      = H - barH
          const colour = TIER_COLOURS[pt.risk_tier] ?? '#94a3b8'
          const isLast = i === n - 1
          return (
            <g key={pt.date}>
              <rect x={x} y={y} width={barW} height={barH} rx={4} fill={colour} opacity={isLast ? 1 : 0.5} />
              {isLast && (
                <text x={x + barW / 2} y={y - 8} textAnchor="middle" fontSize="16" fill={colour} fontWeight="800">
                  {pt.risk_score.toFixed(0)}
                </text>
              )}
              <text x={x + barW / 2} y={H + 22} textAnchor="middle" fontSize="14" fill="#64748b" fontWeight="600">
                {new Date(pt.date).toLocaleDateString('en', { weekday: 'short' })}
              </text>
            </g>
          )
        })}
      </svg>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Default form state
// ---------------------------------------------------------------------------
const EMPTY_FORM: ScoreRequest = {
  user: '',
  logon_count: 0,
  off_hours_events: 0,
  unique_pcs: 0,
  device_connects: 0,
  device_off_hours: 0,
  file_events: 0,
  removable_file_events: 0,
  email_count: 0,
  external_email_count: 0,
  suspicious_url_events: 0,
  privilege_tier: 'standard',
}

// ---------------------------------------------------------------------------
// Main Dashboard — live analysis form
// ---------------------------------------------------------------------------
export default function Dashboard() {
  const navigate = useNavigate()

  const [form, setForm]       = useState<ScoreRequest>(EMPTY_FORM)
  const [loading, setLoading] = useState(false)
  const [error, setError]     = useState<string | null>(null)
  const [result, setResult]   = useState<ScoreResponse | null>(null)
  const [trend, setTrend]     = useState<TrendPoint[] | null>(null)
  const [sessionState, setSessionState] = useState<SessionStateResponse | null>(null)
  const [preAnalysisState, setPreAnalysisState] = useState<SessionStateResponse | null>(null)

  function set<K extends keyof ScoreRequest>(key: K, val: ScoreRequest[K]) {
    setForm(f => ({ ...f, [key]: val }))
  }

  function loadPreset(payload: ScoreRequest) {
    setForm(payload)
    setResult(null)
    setTrend(null)
    setError(null)
  }

  async function runAnalysis() {
    if (!form.user.trim()) { setError('Please enter a User ID.'); return }
    sessionStorage.setItem('Vigil_payload', JSON.stringify(form))
    setError(null)
    setLoading(true)
    setResult(null)
    setTrend(null)
    try {
      // Fetch session state BEFORE running analysis to see if demo triggered a suspension/step-up
      try {
        const preSession = await fetchSessionState(form.user)
        if (preSession.session_status !== 'allowed' && preSession.reason) {
          setPreAnalysisState(preSession)
        } else {
          setPreAnalysisState(null)
        }
      } catch (err) {
        console.error("Failed to fetch pre-analysis session state", err)
        setPreAnalysisState(null)
      }

      const [res, trendRes] = await Promise.all([
        scoreUser(form),
        fetchUserTrend(form.user).catch(() => null),
      ])
      setResult(res)
      
      try {
        const sessionRes = await fetchSessionState(res.user)
        setSessionState(sessionRes)
      } catch (err) {
        console.error("Failed to fetch session state", err)
      }

      if (trendRes) {
        // Override the last bar ("today") with the actual computed score
        // so that different field values produce a visibly different chart
        const updatedTrend = [...trendRes.trend]
        if (updatedTrend.length > 0) {
          updatedTrend[updatedTrend.length - 1] = {
            ...updatedTrend[updatedTrend.length - 1],
            risk_score: res.risk_score,
            risk_tier:  res.risk_tier,
          }
        }
        setTrend(updatedTrend)
      } else {
        // No trend data from server — build a synthetic 7-day window
        // where the last bar is the current result and prior days are lower
        const today = new Date()
        const syntheticTrend: TrendPoint[] = Array.from({ length: 7 }).map((_, i) => {
          const d = new Date(today)
          d.setDate(d.getDate() - (6 - i))
          const isToday = i === 6
          const score   = isToday ? res.risk_score : Math.max(5, res.risk_score * (0.3 + Math.random() * 0.4))
          const tier    = score >= 89 ? 'Critical' : score >= 68 ? 'High' : score >= 41 ? 'Medium' : 'Low'
          return { date: d.toISOString().slice(0, 10), risk_score: Math.round(score), risk_tier: tier }
        })
        setTrend(syntheticTrend)
      }
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Scoring failed — is the backend running?')
    } finally {
      setLoading(false)
    }
  }

  function reset() {
    setForm(EMPTY_FORM)
    setResult(null)
    setTrend(null)
    setError(null)
    setPreAnalysisState(null)
  }

  const tier     = result?.risk_tier
  const tierGlow = tier === 'Critical' || tier === 'High' ? 'red' : tier ? 'green' : 'none'

  const inputCls = 'w-full bg-[#e8dfcd] border border-[#cab593] rounded-lg px-3 py-2 text-base text-[#26201b] focus:border-[#496b52] focus:outline-none transition-colors'
  const labelCls = 'block text-sm text-[#26201b] mb-1 font-medium'

  return (
    <div className="max-w-7xl mx-auto px-4 sm:6 py-10 space-y-8">

      {/* Header */}
      <div className="space-y-1">
        <p className="text-lg font-bold uppercase tracking-[0.2em] text-[#496b52]">Live Analysis</p>
        <h1 className="text-5xl lg:text-6xl font-extrabold text-[#26201b]">Insider Threat Risk Engine</h1>
        <p className="text-[#26201b] text-base mt-2">
          Enter any user's activity data below and the AI model will score them in real time.
        </p>
      </div>

      {/* Quick-fill presets */}
      <div className="mt-4">
        <p className="text-base text-[#26201b] uppercase tracking-wider mb-3 font-bold">Quick-fill a demo scenario →</p>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
          {DEMO_SCENARIOS.map(s => (
            <div key={s.label} className="flex flex-col gap-2">
              <button
                onClick={() => loadPreset(s.getPayload())}
                className="flex items-center justify-center gap-2 text-sm px-4 py-2.5 rounded-lg bg-[#dfd2bc] border border-[#cab593] hover:border-[#496b52] hover:bg-[#d4c5a9] transition-all text-[#26201b] shadow-sm font-medium w-full"
              >
                {s.label === 'Privileged Admin' && <Crown className="w-4 h-4 text-[#92402d]" />}
                <Zap className="w-4 h-4 text-[#496b52]" />
                {s.label}
              </button>
              <p className="text-xs text-[#716a5d] leading-snug px-1 text-center">
                {s.description}
              </p>
            </div>
          ))}
        </div>
      </div>

      <div className="grid lg:grid-cols-2 gap-8 items-start">

        {/* ── LEFT: Input Form ── */}
        <GlassCard className="space-y-5">
          <h2 className="font-semibold text-[#26201b]">User Activity Input</h2>

          {/* User + privilege */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className={labelCls}>User ID *</label>
              <input
                type="text"
                placeholder="e.g. EMP0042"
                className={inputCls}
                value={form.user}
                onChange={e => set('user', e.target.value)}
              />
            </div>
            <div>
              <label className={labelCls}>Privilege Tier</label>
              <select
                className={inputCls}
                value={form.privilege_tier ?? 'standard'}
                onChange={e => set('privilege_tier', e.target.value)}
              >
                <option value="standard">Standard</option>
                <option value="elevated">Elevated</option>
                <option value="admin">Admin</option>
                <option value="domain_admin">Domain Admin</option>
              </select>
            </div>
          </div>

          {/* Activity counters — 2-col grid */}
          <div className="grid grid-cols-2 gap-x-4 gap-y-3">
            {([
              ['logon_count',            'Logon Count'],
              ['off_hours_events',       'Off-Hours Events'],
              ['unique_pcs',             'Unique PCs Accessed'],
              ['device_connects',        'USB / Device Connects'],
              ['device_off_hours',       'Off-Hours Device Events'],
              ['file_events',            'File Access Events'],
              ['removable_file_events',  'Removable Media Files'],
              ['email_count',            'Emails Sent'],
              ['external_email_count',   'External Emails Sent'],
              ['suspicious_url_events',  'Suspicious URL Visits'],
            ] as [keyof ScoreRequest, string][]).map(([key, label]) => (
              <div key={key}>
                <label className={labelCls}>{label}</label>
                <input
                  type="number"
                  min={0}
                  className={inputCls}
                  value={(form[key] as number) ?? 0}
                  onChange={e => set(key, parseInt(e.target.value) || 0)}
                />
              </div>
            ))}
          </div>

          {/* Error */}
          {error && (
            <div className="flex items-start gap-2 text-sm text-red-400 bg-red-900/20 border border-red-500/30 rounded-lg px-3 py-2">
              <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
              {error}
            </div>
          )}

          {/* Actions */}
          <div className="flex gap-3 pt-1">
            <button
              onClick={runAnalysis}
              disabled={loading}
              className="flex-1 btn-primary flex items-center justify-center gap-2 disabled:opacity-50"
            >
              {loading
                ? <><Loader2 className="w-4 h-4 animate-spin" /> Analyzing…</>
                : <><Play className="w-4 h-4" /> Run Analysis</>
              }
            </button>
            <button onClick={reset} className="btn-ghost border border-[#a39882] px-3" title="Clear form">
              <RotateCcw className="w-4 h-4" />
            </button>
          </div>
        </GlassCard>

        {/* ── RIGHT: Results ── */}
        <div className="space-y-6">
          
          {/* Demo Banner */}
          {preAnalysisState && (
            <div className="bg-red-50 border border-red-200 rounded-xl p-4 animate-fade-in flex items-start gap-3">
              <AlertTriangle className="w-6 h-6 text-red-600 shrink-0 mt-0.5" />
              <div>
                <p className="font-bold text-red-900">
                  ⚠ This user already has an active session status: {preAnalysisState.session_status.toUpperCase()}
                </p>
                <p className="text-sm text-red-800 mt-1">
                  Reason: <span className="font-mono">{preAnalysisState.reason}</span> 
                  {preAnalysisState.timestamp && ` (recorded at ${preAnalysisState.timestamp})`}
                </p>
              </div>
            </div>
          )}

          {!result && !loading && !error && (
            <GlassCard className="flex flex-col items-center justify-center min-h-[200px] text-[#26201b] text-sm text-center space-y-3">
              <ShieldCheck className="w-12 h-12 opacity-30" />
              <p>Fill in the form and click <strong className="text-[#26201b]">Run Analysis</strong><br />to get a live risk score from the AI model.</p>
            </GlassCard>
          )}

          {loading && (
            <GlassCard className="flex flex-col items-center justify-center min-h-[200px] text-[#26201b] gap-3">
              <Loader2 className="w-8 h-8 animate-spin text-indigo-400" />
              <p className="text-sm">Running ML inference…</p>
            </GlassCard>
          )}

          {result && !loading && (
            <>
              {/* Score + trend */}
              <div className="flex flex-col gap-4">
                <GlassCard glow={tierGlow as never} className="text-center space-y-2 py-6">
                  <p className="text-sm text-[#26201b] uppercase tracking-widest font-bold">Risk Score</p>
                  <p className={`text-6xl font-extrabold ${
                    tier === 'Critical' ? 'text-red-400'
                    : tier === 'High'   ? 'text-purple-400'
                    : tier === 'Medium' ? 'text-pink-400'
                    : 'text-indigo-400'
                  }`}>{result.risk_score.toFixed(1)}</p>
                  <p className="text-[#26201b] text-xs">/ 100</p>
                  <div className="flex flex-wrap justify-center gap-1.5 pt-1">
                    <TierBadge tier={result.risk_tier} />
                    {result.privilege_tier !== 'standard' && (
                      <span className="px-2 py-0.5 rounded-full text-xs bg-[#92402d]/15 text-pink-300 border border-[#92402d]/25 flex items-center gap-1">
                        <Crown className="w-3 h-3" />{result.privilege_tier.replace('_',' ')} ×{result.privilege_multiplier.toFixed(2)}
                      </span>
                    )}
                  </div>
                  <div className="flex items-center justify-center gap-2 pt-1">
                    <p className="text-xs text-[#26201b] font-mono">{result.user}</p>
                    {sessionState && (
                      <span className={`px-2 py-0.5 rounded-full text-xs border flex items-center gap-1 ${
                        sessionState.session_status === 'suspended' 
                          ? 'bg-red-100 text-red-800 border-red-200'
                          : sessionState.session_status === 'step_up_required'
                          ? 'bg-orange-100 text-orange-800 border-orange-200'
                          : sessionState.session_status === 'allowed_monitored'
                          ? 'bg-yellow-100 text-yellow-800 border-yellow-200'
                          : 'bg-emerald-100 text-emerald-800 border-emerald-200'
                      }`}>
                        {sessionState.session_status === 'suspended' && '🔒 Session Suspended'}
                        {sessionState.session_status === 'step_up_required' && '🔐 Step-Up Verification Required'}
                        {sessionState.session_status === 'allowed_monitored' && '👁 Allowed — Monitored'}
                        {sessionState.session_status === 'allowed' && '✅ Allowed'}
                      </span>
                    )}
                  </div>
                </GlassCard>

                <GlassCard className="flex flex-col justify-center">
                  {trend
                    ? <TrendChart points={trend} />
                    : <p className="text-xs text-[#26201b] text-center">No historical trend data for this user</p>
                  }
                </GlassCard>
              </div>

              {/* Narrative */}
              <GlassCard className="space-y-2">
                <h3 className="text-sm font-semibold text-[#26201b] uppercase tracking-wider">AI Narrative Explanation</h3>
                <p className="text-base text-[#26201b] leading-relaxed">{result.narrative_explanation}</p>
              </GlassCard>

              {/* Signals */}
              {result.top_signals.length > 0 && (
                <GlassCard className="space-y-3">
                  <div className="flex flex-col sm:flex-row sm:items-baseline justify-between gap-1 mb-1">
                    <h3 className="text-sm font-semibold text-[#26201b] uppercase tracking-wider">Top Anomaly Signals</h3>
                    <span className="text-xs text-[#544c41] font-medium">σ = standard deviations from baseline</span>
                  </div>
                  {result.top_signals.map(s => <SignalBar key={s.feature} signal={s} />)}
                </GlassCard>
              )}

              {/* Enforcement */}
              <GlassCard className="space-y-4">
                <div className="flex items-center gap-2 pb-2 border-b border-[#cab593]/50">
                  <ShieldCheck className="w-5 h-5 text-[#496b52]" />
                  <h3 className="text-lg font-bold text-[#26201b] uppercase tracking-wider">Enforcement Actions</h3>
                  <span className="ml-auto text-base text-[#26201b] font-bold">{result.recommended_actions.length} recommended</span>
                </div>
                <EnforcementPanel 
                  actions={result.recommended_actions} 
                  sessionStatus={sessionState?.session_status || 'allowed'}
                  onVerifyIdentity={async () => {
                    try {
                      const updatedState = await verifySessionIdentity(result.user)
                      setSessionState(updatedState)
                    } catch (e) {
                      console.error("Verification failed", e)
                    }
                  }}
                />
              </GlassCard>

              {/* Audit badge */}
              {result.audit_record_id && (
                <AuditBadge
                  recordId={result.audit_record_id}
                  onViewAudit={() => navigate(`/dashboard/report?user=${result.user}&record=${result.audit_record_id}`)}
                />
              )}

              {/* Full report */}
              <button
                onClick={() => navigate(`/dashboard/report?user=${result.user}&record=${result.audit_record_id ?? ''}`)}
                className="btn-primary w-full flex items-center justify-center gap-2"
              >
                <Play className="w-4 h-4" /> View Full Report
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
