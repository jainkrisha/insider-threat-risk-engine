import { useEffect, useState } from 'react'
import { useSearchParams, Link } from 'react-router-dom'
import {
  User, Clock, Lock, Download, AlertTriangle,
  Loader2, LogIn, Monitor, Mail, Globe, TrendingDown, TrendingUp
} from 'lucide-react'
import GlassCard from '../components/GlassCard'
import TierBadge from '../components/TierBadge'
import AuditBadge from '../components/AuditBadge'
import SignalBar from '../components/SignalBar'
import { scoreUser, fetchVaultEntry, DEMO_SCENARIOS, type ScoreResponse, type VaultEntry } from '../api'

// Small stat card
function StatCard({ label, value, icon }: { label: string; value: string | number; icon: React.ReactNode }) {
  return (
    <GlassCard className="flex items-center gap-4 py-5">
      <div className="w-10 h-10 rounded-xl bg-slate-800 flex items-center justify-center shrink-0">
        {icon}
      </div>
      <div>
        <p className="text-2xl font-bold">{value}</p>
        <p className="text-xs text-slate-400 mt-0.5">{label}</p>
      </div>
    </GlassCard>
  )
}

export default function Report() {
  const [params]    = useSearchParams()
  const userId      = params.get('user')   ?? ''
  const recordId    = params.get('record') ?? ''

  const [scoreData,  setScoreData]  = useState<ScoreResponse | null>(null)
  const [vaultData,  setVaultData]  = useState<VaultEntry | null>(null)
  const [loading,    setLoading]    = useState(true)
  const [error,      setError]      = useState<string | null>(null)

  useEffect(() => {
    if (!userId) { setError('No user specified.'); setLoading(false); return }

    // Find the matching scenario payload so we can re-score with the same values
    const scenario = DEMO_SCENARIOS.find(s => s.payload.user === userId)
    const payload  = scenario?.payload ?? { user: userId }

    const tasks: Promise<void>[] = [
      scoreUser(payload).then(r => setScoreData(r)).catch(e => { throw e }),
    ]
    if (recordId) {
      tasks.push(fetchVaultEntry(recordId).then(v => setVaultData(v)).catch(() => {}))
    }

    Promise.all(tasks)
      .catch(e => setError(e instanceof Error ? e.message : 'Failed to load report'))
      .finally(() => setLoading(false))
  }, [userId, recordId])

  const timestamp = vaultData?.audit_entry.timestamp
    ?? (scoreData ? new Date().toISOString() : null)

  function handleExportCSV() {
    if (!scoreData) return
    const rows = [
      ['Field', 'Value'],
      ['User', scoreData.user],
      ['Risk Score', scoreData.risk_score],
      ['Risk Tier', scoreData.risk_tier],
      ['Narrative', scoreData.narrative_explanation],
      ['Actions', scoreData.recommended_actions.join('; ')],
      ['Audit Record ID', recordId || 'N/A'],
      ['Timestamp', timestamp ?? 'N/A'],
    ]
    const csv     = rows.map(r => r.map(c => `"${c}"`).join(',')).join('\n')
    const blob    = new Blob([csv], { type: 'text/csv' })
    const url     = URL.createObjectURL(blob)
    const a       = document.createElement('a')
    a.href = url; a.download = `finspark_report_${scoreData.user}.csv`; a.click()
    URL.revokeObjectURL(url)
  }

  // ─── loading / error states ───────────────────────────────────────────────
  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh] gap-3 text-slate-400">
        <Loader2 className="w-5 h-5 animate-spin" /> Loading report for {userId}…
      </div>
    )
  }
  if (error || !scoreData) {
    return (
      <div className="max-w-lg mx-auto px-4 py-16 text-center space-y-4">
        <AlertTriangle className="w-10 h-10 text-red-400 mx-auto" />
        <p className="text-lg font-semibold">{error ?? 'No data found'}</p>
        <Link to="/dashboard" className="btn-primary inline-flex">← Back to Dashboard</Link>
      </div>
    )
  }

  const tier = scoreData.risk_tier
  const tierGlow = tier === 'Critical' || tier === 'High' ? 'red' : 'green'

  // Summary stats — pull from the scenario payload we scored with
  const scenario = DEMO_SCENARIOS.find(s => s.payload.user === userId)
  const p        = scenario?.payload

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 py-12 space-y-8 animate-fade-in">

      {/* Header */}
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="space-y-1">
          <p className="section-label">Full Report</p>
          <h1 className="text-3xl font-bold flex items-center gap-3">
            <User className="w-6 h-6 text-slate-400" />
            {scoreData.user}
          </h1>
          {timestamp && (
            <p className="text-sm text-slate-400 flex items-center gap-1.5 mt-1">
              <Clock className="w-3.5 h-3.5" />
              Last analysed: {new Date(timestamp).toLocaleString()}
            </p>
          )}
        </div>
        <div className="flex items-center gap-3 flex-wrap">
          <TierBadge tier={tier} />
          <button onClick={handleExportCSV} className="btn-ghost border border-white/10 flex items-center gap-2 text-sm">
            <Download className="w-4 h-4" /> Export CSV
          </button>
        </div>
      </div>

      {/* Summary stats */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <StatCard label="Logons today"     value={p?.logon_count ?? 0}             icon={<LogIn   className="w-5 h-5 text-indigo-400"  />} />
        <StatCard label="Off-hours events" value={p?.off_hours_events ?? 0}        icon={<Clock   className="w-5 h-5 text-orange-400"/>} />
        <StatCard label="Unique devices"   value={p?.device_connects ?? 0}         icon={<Monitor className="w-5 h-5 text-emerald-400"/>} />
        <StatCard label="External emails"  value={p?.external_email_count ?? 0}    icon={<Mail    className="w-5 h-5 text-yellow-400"/>} />
      </div>

      {/* Score + narrative */}
      <div className="grid sm:grid-cols-2 gap-5">
        <GlassCard glow={tierGlow as never} className="text-center space-y-3">
          <p className="text-sm text-slate-400 uppercase tracking-widest">Risk Score</p>
          <p className={`text-6xl font-extrabold ${
            tier === 'Critical' ? 'text-red-400'
            : tier === 'High'   ? 'text-orange-400'
            : tier === 'Medium' ? 'text-yellow-400'
            : 'text-emerald-400'
          }`}>
            {scoreData.risk_score.toFixed(1)}
          </p>
          <TierBadge tier={tier} />
        </GlassCard>

        <GlassCard className="space-y-3">
          <h2 className="font-semibold text-sm text-slate-300 uppercase tracking-wider">
            Narrative Explanation
          </h2>
          <p className="text-sm text-slate-300 leading-relaxed">{scoreData.narrative_explanation}</p>
        </GlassCard>
      </div>

      {/* Signal breakdown */}
      <GlassCard className="space-y-4">
        <h2 className="font-semibold text-sm text-slate-300 uppercase tracking-wider">
          Anomaly Signal Breakdown
        </h2>
        {scoreData.top_signals.length > 0 ? (
          <div className="divide-y divide-slate-700/50">
            {scoreData.top_signals.map(s => (
              <div key={s.feature} className="py-2 first:pt-0 last:pb-0">
                <SignalBar signal={s} />
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-slate-500">No significant anomalies detected for this session.</p>
        )}
      </GlassCard>

      {/* Activity table — synthetic rows representing the analysed features */}
      <GlassCard className="space-y-4">
        <h2 className="font-semibold text-sm text-slate-300 uppercase tracking-wider">
          Session Activity Summary
        </h2>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-xs text-slate-500 uppercase tracking-wider border-b border-slate-700">
                <th className="text-left py-2 pr-6">Feature</th>
                <th className="text-right py-2 pr-6">Value</th>
                <th className="text-left py-2">Assessment</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800">
              {[
                { feature: 'Logon Events',      value: p?.logon_count ?? 0,          signal: scoreData.top_signals.find(s => s.feature === 'logon_count') },
                { feature: 'Off-Hours Events',  value: p?.off_hours_events ?? 0,     signal: scoreData.top_signals.find(s => s.feature === 'off_hours_events') },
                { feature: 'Suspicious URLs',   value: p?.suspicious_url_events ?? 0, signal: scoreData.top_signals.find(s => s.feature === 'suspicious_url_events') },
                { feature: 'External Emails',   value: p?.external_email_count ?? 0, signal: scoreData.top_signals.find(s => s.feature === 'external_email_count') },
                { feature: 'Device Connects',   value: p?.device_connects ?? 0,      signal: scoreData.top_signals.find(s => s.feature === 'device_connects') },
                { feature: 'Removable Files',   value: p?.removable_file_events ?? 0,signal: scoreData.top_signals.find(s => s.feature === 'removable_file_events') },
              ].map(row => {
                const z        = row.signal?.zscore ?? 0
                const isSpike  = z > 1
                const isDrop   = z < -1.5
                const isFlag   = isSpike || isDrop
                return (
                  <tr key={row.feature} className={isFlag ? 'bg-red-900/10' : ''}>
                    <td className="py-2.5 pr-6 text-slate-300">{row.feature}</td>
                    <td className="py-2.5 pr-6 text-right font-mono">{row.value}</td>
                    <td className="py-2.5">
                      {isFlag ? (
                        <span className={`inline-flex items-center gap-1 text-xs ${isDrop ? 'text-orange-400' : 'text-red-400'}`}>
                          {isDrop
                            ? <TrendingDown className="w-3.5 h-3.5" />
                            : <TrendingUp   className="w-3.5 h-3.5" />
                          }
                          {isDrop ? 'Sharp drop' : 'Spike'} ({z > 0 ? '+' : ''}{z.toFixed(1)}σ)
                        </span>
                      ) : (
                        <span className="text-xs text-slate-600 flex items-center gap-1">
                          <Globe className="w-3 h-3" /> Within baseline
                        </span>
                      )}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </GlassCard>

      {/* Recommended Actions */}
      <GlassCard className="space-y-3">
        <h2 className="font-semibold text-sm text-slate-300 uppercase tracking-wider">
          Recommended Actions
        </h2>
        {scoreData.recommended_actions.length > 0 ? (
          <div className="flex flex-wrap gap-2">
            {scoreData.recommended_actions.map(a => (
              <span key={a} className="px-3 py-1.5 bg-slate-800 border border-slate-700 rounded-lg text-xs font-mono text-slate-300">
                {a.replace(/_/g, ' ')}
              </span>
            ))}
          </div>
        ) : (
          <p className="text-sm text-slate-500">No strict actions required.</p>
        )}
      </GlassCard>

      {/* Vault audit section */}
      {recordId && (
        <div className="space-y-3">
          <div className="flex items-center gap-2">
            <Lock className="w-4 h-4 text-indigo-400" />
            <h2 className="font-semibold text-sm text-slate-300 uppercase tracking-wider">
              Audit Record
            </h2>
          </div>
          <AuditBadge recordId={recordId} />
          {vaultData && (
            <GlassCard className="space-y-2 border-indigo-500/15">
              <p className="text-xs text-slate-500 font-medium uppercase tracking-wider">
                Decrypted vault entry (verified)
              </p>
              <pre className="text-xs text-slate-300 font-mono overflow-x-auto whitespace-pre-wrap leading-relaxed">
                {JSON.stringify(vaultData.audit_entry, null, 2)}
              </pre>
            </GlassCard>
          )}
        </div>
      )}

      {/* Footer nav */}
      <div className="flex gap-3 pt-4">
        <Link to="/dashboard" className="btn-ghost border border-white/10 text-sm">
          ← Back to Dashboard
        </Link>
      </div>

    </div>
  )
}
