// Typed wrappers for all FastAPI endpoints used by the frontend.
// The backend is untouched — we just consume it via fetch.

export interface TopSignal {
  feature: string
  zscore: number
  label: string
}

export interface ScoreResponse {
  user: string
  risk_score: number
  risk_tier: 'Low' | 'Medium' | 'High' | 'Critical'
  model_version: string
  top_signals: TopSignal[]
  recommended_actions: string[]
  narrative_explanation: string
  audit_record_id: string | null
}

export interface VaultEntry {
  record_id: string
  audit_entry: {
    user_id: string
    risk_tier: string
    action_taken: string[]
    explanation: string
    timestamp: string
    session_id: string
  }
}

export interface ScoreRequest {
  user: string
  day?: string
  logon_count?: number
  off_hours_events?: number
  unique_pcs?: number
  device_connects?: number
  device_off_hours?: number
  file_events?: number
  removable_file_events?: number
  email_count?: number
  external_email_count?: number
  suspicious_url_events?: number
}

// ─── API calls ───────────────────────────────────────────────────────────────

export async function scoreUser(req: ScoreRequest): Promise<ScoreResponse> {
  const res = await fetch('/score', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Unknown error' }))
    throw new Error(err.detail ?? `HTTP ${res.status}`)
  }
  return res.json()
}

export async function fetchVaultEntry(recordId: string): Promise<VaultEntry> {
  const res = await fetch(`/vault/${recordId}`)
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Unknown error' }))
    throw new Error(err.detail ?? `HTTP ${res.status}`)
  }
  return res.json()
}

export async function checkHealth(): Promise<{ status: string; model_loaded: boolean }> {
  const res = await fetch('/health')
  if (!res.ok) throw new Error('API unhealthy')
  return res.json()
}

// ─── Demo presets that map to the existing /score payload format ──────────────

export interface DemoScenario {
  label: string
  description: string
  tier: string
  payload: ScoreRequest
}

export const DEMO_SCENARIOS: DemoScenario[] = [
  {
    label: 'Critical Threat',
    description: 'Mass data exfiltration — high off-hours activity, USB transfers, suspicious browsing',
    tier: 'Critical',
    payload: {
      user: 'CCA0046',
      logon_count: 5,
      off_hours_events: 10,
      suspicious_url_events: 24,
      external_email_count: 8,
      removable_file_events: 12,
      device_connects: 6,
      email_count: 30,
    },
  },
  {
    label: 'Slow-Burn Exfiltration',
    description: 'Scenario 2 — moderately elevated activity sustained over many days',
    tier: 'High',
    payload: {
      user: 'MAS0025',
      logon_count: 8,
      off_hours_events: 4,
      suspicious_url_events: 2,
      external_email_count: 6,
      removable_file_events: 3,
      email_count: 45,
    },
  },
  {
    label: 'Normal User',
    description: 'Typical low-risk employee — activity within expected baseline',
    tier: 'Low',
    payload: {
      user: 'BAL0044',
      logon_count: 3,
      off_hours_events: 0,
      suspicious_url_events: 0,
      external_email_count: 1,
      email_count: 12,
    },
  },
]
