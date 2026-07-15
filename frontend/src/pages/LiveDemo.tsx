import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Shield, Play } from 'lucide-react'
import GlassCard from '../components/GlassCard'
import TierBadge from '../components/TierBadge'
import { scoreUser, type ScoreResponse } from '../api'

export default function LiveDemo() {
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<ScoreResponse | null>(null)
  
  const [form, setForm] = useState({
    user: 'CCA0046',
    logon_count: 0,
    off_hours_events: 0,
    suspicious_url_events: 0,
    external_email_count: 0,
  })

  function loadDemo(type: 'critical' | 'normal') {
    if (type === 'critical') {
      setForm({
        user: 'CCA0046',
        logon_count: 5,
        off_hours_events: 10,
        suspicious_url_events: 24,
        external_email_count: 8,
      })
    } else {
      setForm({
        user: 'BAL0044',
        logon_count: 1,
        off_hours_events: 0,
        suspicious_url_events: 0,
        external_email_count: 0,
      })
    }
  }

  async function handleAnalyze() {
    setLoading(true)
    try {
      const res = await scoreUser(form)
      setResult(res)
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  const tierGlow = result
    ? result.risk_tier === 'Critical' || result.risk_tier === 'High' ? 'red' : 'green'
    : 'none'

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 py-12 animate-fade-in">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        
        {/* Input Panel */}
        <GlassCard className="p-6">
          <h2 className="text-xl font-bold mb-4">Analyze User Activity</h2>
          
          <div className="flex gap-2 mb-6">
            <button onClick={() => loadDemo('critical')} className="text-xs bg-slate-700 hover:bg-slate-600 px-3 py-1.5 rounded transition">
              Demo: Critical Threat
            </button>
            <button onClick={() => loadDemo('normal')} className="text-xs bg-slate-700 hover:bg-slate-600 px-3 py-1.5 rounded transition">
              Demo: Normal User
            </button>
          </div>

          <div className="space-y-4">
            <div>
              <label className="text-sm text-slate-400 block mb-1">User ID</label>
              <input 
                type="text" 
                className="w-full bg-slate-900/50 rounded-lg p-2.5 text-white border border-slate-700 focus:border-indigo-500 outline-none" 
                value={form.user} 
                onChange={e => setForm({ ...form, user: e.target.value })} 
              />
            </div>
            
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-sm text-slate-400 block mb-1">Logon Count</label>
                <input 
                  type="number" 
                  className="w-full bg-slate-900/50 rounded-lg p-2.5 text-white border border-slate-700 focus:border-indigo-500 outline-none" 
                  value={form.logon_count} 
                  onChange={e => setForm({ ...form, logon_count: parseInt(e.target.value) || 0 })} 
                />
              </div>
              <div>
                <label className="text-sm text-slate-400 block mb-1">Off-Hours Events</label>
                <input 
                  type="number" 
                  className="w-full bg-slate-900/50 rounded-lg p-2.5 text-white border border-slate-700 focus:border-indigo-500 outline-none" 
                  value={form.off_hours_events} 
                  onChange={e => setForm({ ...form, off_hours_events: parseInt(e.target.value) || 0 })} 
                />
              </div>
              <div>
                <label className="text-sm text-slate-400 block mb-1">Suspicious URLs</label>
                <input 
                  type="number" 
                  className="w-full bg-slate-900/50 rounded-lg p-2.5 text-white border border-slate-700 focus:border-indigo-500 outline-none" 
                  value={form.suspicious_url_events} 
                  onChange={e => setForm({ ...form, suspicious_url_events: parseInt(e.target.value) || 0 })} 
                />
              </div>
              <div>
                <label className="text-sm text-slate-400 block mb-1">External Emails</label>
                <input 
                  type="number" 
                  className="w-full bg-slate-900/50 rounded-lg p-2.5 text-white border border-slate-700 focus:border-indigo-500 outline-none" 
                  value={form.external_email_count} 
                  onChange={e => setForm({ ...form, external_email_count: parseInt(e.target.value) || 0 })} 
                />
              </div>
            </div>

            <button 
              onClick={handleAnalyze} 
              disabled={loading}
              className="w-full mt-4 bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 py-3 rounded-xl font-semibold shadow-glow-purple transition-all active:scale-[0.98] disabled:opacity-50 text-white"
            >
              {loading ? 'Analyzing...' : 'Run Analysis'}
            </button>
          </div>
        </GlassCard>

        {/* Results Panel */}
        <GlassCard glow={tierGlow as never} className="p-6 flex flex-col items-center justify-center min-h-[400px]">
          {!result ? (
            <div className="text-slate-500 text-center animate-fade-in">
              <Shield className="w-16 h-16 mx-auto mb-4 opacity-50" />
              <p>Run an analysis to see risk insights</p>
            </div>
          ) : (
            <div className="w-full animate-fade-in space-y-5">
              <div className="text-center mb-6">
                <p className="text-sm text-slate-400 uppercase tracking-widest">Risk Score</p>
                <div className={`text-6xl font-extrabold my-2 ${
                  result.risk_tier === 'Critical' ? 'text-red-400'
                  : result.risk_tier === 'High' ? 'text-orange-400'
                  : result.risk_tier === 'Medium' ? 'text-yellow-400'
                  : 'text-emerald-400'
                }`}>
                  {result.risk_score.toFixed(1)}
                </div>
                <TierBadge tier={result.risk_tier} />
              </div>

              <div className="bg-slate-900/50 p-4 rounded-xl border border-slate-700/50">
                <h4 className="text-sm font-semibold text-slate-300 mb-2">Narrative Explanation</h4>
                <p className="text-sm text-slate-300 leading-relaxed">{result.narrative_explanation}</p>
              </div>

              <div className="bg-slate-900/50 p-4 rounded-xl border border-slate-700/50">
                <h4 className="text-sm font-semibold text-slate-300 mb-2">Recommended Actions</h4>
                {result.recommended_actions.length > 0 ? (
                  <ul className="text-sm text-slate-300 list-disc list-inside">
                    {result.recommended_actions.map(a => (
                      <li key={a}>{a.replace(/_/g, ' ').toUpperCase()}</li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-sm text-slate-500">No strict actions required</p>
                )}
              </div>

              {result.audit_record_id && (
                <div className="bg-indigo-950/40 border border-indigo-500/40 p-4 rounded-xl text-sm text-indigo-300 flex items-start gap-3">
                  <span className="text-xl leading-none mt-0.5">🔒</span>
                  <div>
                    <strong className="text-indigo-200 block mb-1">Audit entry encrypted</strong>
                    (hybrid: X25519 + ML-KEM-768)<br />
                    <span className="text-xs text-indigo-400 mt-1 block">
                      Record ID: <code className="font-mono text-indigo-200">{result.audit_record_id}</code>
                    </span>
                  </div>
                </div>
              )}
            </div>
          )}
        </GlassCard>

      </div>
    </div>
  )
}
