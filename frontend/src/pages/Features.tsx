import GlassCard from '../components/GlassCard'
import { Brain, Zap, Shield, Lock, BarChart3, Link2 } from 'lucide-react'

const FEATURES = [
  {
    icon: <Brain className="w-6 h-6 text-indigo-400" />,
    title: 'Hybrid AI Risk Engine',
    subtitle: 'Isolation Forest + Random Forest',
    body: `An unsupervised Isolation Forest (60% weight) learns what each user's "normal" looks like
      and fires on statistical anomalies — no labels required. A supervised Random Forest (40%)
      is trained on known insider threat patterns to boost recall on confirmed scenarios.
      Scores are aggregated with a composite formula (max day, mean day, high-risk day rate) so
      slow-burn exfiltrators are caught alongside one-day spikes.`,
    accent: 'border-[#496b52]/20',
  },
  {
    icon: <BarChart3 className="w-6 h-6 text-indigo-400" />,
    title: 'Explainable AI (XAI)',
    subtitle: 'Per-user z-score deviation breakdowns',
    body: `Every risk verdict includes a ranked list of the top contributing signals with their
      z-scores relative to that individual's personal baseline. The narrative distinguishes
      between anomalous SPIKES (e.g. "15 off-hours logins vs. normal ~3.7") and sharp DROPS
      (e.g. "0 logons vs. normal ~4.9 — consistent with a dormant or compromised account").
      No generic catch-all sentences.`,
    accent: 'border-[#496b52]/20',
  },
  {
    icon: <Zap className="w-6 h-6 text-pink-400" />,
    title: 'Real-Time Detection API',
    subtitle: 'FastAPI · /score endpoint',
    body: `A production-ready FastAPI backend scores a user's activity in milliseconds.
      Send a JSON payload with the user ID and behavioural metrics, get back a risk score (0-100),
      tier (Low / Medium / High / Critical), ranked anomaly signals, and access control
      recommendations. Swagger UI at /docs.`,
    accent: 'border-[#92402d]/20',
  },
  {
    icon: <Shield className="w-6 h-6 text-purple-400" />,
    title: 'Risk-Based Access Control',
    subtitle: 'Automatic action recommendations',
    body: `Based on the risk tier, the engine recommends concrete security actions:
      Critical → require_mfa + restrict_removable_media + alert_soc_immediately.
      High → require_mfa + log_enhanced.
      Medium → log_standard.
      Actions are returned in the API response and displayed on the dashboard for a human
      analyst to review and approve.`,
    accent: 'border-[#92402d]/20',
  },
  {
    icon: <Lock className="w-6 h-6 text-indigo-400" />,
    title: 'Quantum-Safe Audit Vault',
    subtitle: 'Hybrid X25519 + ML-KEM-768 · NIST FIPS 203',
    body: `Every High or Critical risk event is encrypted and appended to an append-only audit log
      before any action is taken. Encryption uses a genuine hybrid KEM combiner — the same
      pattern used by Chrome and Cloudflare for post-quantum TLS:

      1. X25519 ECDH  → classical_secret  (battle-tested, fast)
      2. ML-KEM-768 encapsulate → pq_secret + 1088-byte ciphertext  (NIST FIPS 203, quantum-resistant)
      3. HKDF-SHA256(classical_secret ‖ pq_secret) → 32-byte AES key
      4. AES-256-GCM encrypt(audit_json) → authenticated ciphertext

      An attacker must break BOTH X25519 and ML-KEM-768 to decrypt a record. The vault is
      implemented in src/vault.py using pyca/cryptography ≥ 48.0 (bundles OpenSSL 3.5+
      with native ML-KEM support — no external C library compilation required).`,
    accent: 'border-[#496b52]/20',
  },
  {
    icon: <Link2 className="w-6 h-6 text-[#26201b]" />,
    title: 'Vault Verification Endpoint',
    subtitle: 'GET /vault/{record_id}',
    body: `Any encrypted audit record can be decrypted on-demand via the /vault/{record_id}
      endpoint — returning the original plaintext JSON for live demo verification. The dashboard
      surfaces the Record ID after each High/Critical analysis so judges can immediately confirm
      the entry was genuinely stored and can be retrieved.`,
    accent: 'border-slate-600/40',
  },
]

export default function Features() {
  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 py-16 space-y-12 animate-fade-in">

      <section className="space-y-4">
        <p className="section-label">Capabilities</p>
        <h1 className="text-4xl font-bold">What Vigil can do</h1>
        <p className="text-[#26201b] text-lg">
          A full breakdown of every feature — from the ML pipeline to the cryptographic vault.
        </p>
      </section>

      <div className="space-y-6">
        {FEATURES.map(f => (
          <GlassCard key={f.title} className={`glass-hover ${f.accent} space-y-3`}>
            <div className="flex items-start gap-4">
              <div className="w-12 h-12 rounded-xl bg-[#e8dfcd] flex items-center justify-center shrink-0 mt-0.5">
                {f.icon}
              </div>
              <div className="flex-1 min-w-0">
                <h2 className="font-bold text-lg">{f.title}</h2>
                <p className="text-xs text-[#26201b] font-mono mt-0.5">{f.subtitle}</p>
                <p className="text-sm text-[#26201b] leading-relaxed mt-3 whitespace-pre-line">{f.body}</p>
              </div>
            </div>
          </GlassCard>
        ))}
      </div>

    </div>
  )
}
