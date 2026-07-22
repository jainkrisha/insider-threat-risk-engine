// Typed wrappers for all FastAPI endpoints used by the frontend.
// The backend is untouched — we just consume it via fetch.

// ---------------------------------------------------------------------------
// Auth header — sent with every protected request
// ---------------------------------------------------------------------------
const API_KEY = import.meta.env.VITE_API_KEY ?? 'demo-Vigil-key'
const AUTH_HEADERS = {
  'Content-Type': 'application/json',
  'X-API-Key': API_KEY,
}

// ---------------------------------------------------------------------------
// Response / request types
// ---------------------------------------------------------------------------
export interface TopSignal {
  feature: string
  zscore: number
  label: string
}

export interface ScoreResponse {
  user: string
  risk_score: number
  risk_tier: 'Low' | 'Medium' | 'High' | 'Critical'
  behavior_score: number
  privilege_tier: string
  privilege_multiplier: number
  hndl_exposure_score: number
  hndl_tier: string
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
    hndl_tier: string
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
  privilege_tier?: string
}

export interface TrendPoint {
  date: string
  risk_score: number
  risk_tier: 'Low' | 'Medium' | 'High' | 'Critical'
}

export interface TrendResponse {
  user: string
  trend: TrendPoint[]
}

// ---------------------------------------------------------------------------
// API calls
// ---------------------------------------------------------------------------

export async function scoreUser(req: ScoreRequest): Promise<ScoreResponse> {
  const res = await fetch('/score', {
    method: 'POST',
    headers: AUTH_HEADERS,
    body: JSON.stringify(req),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Unknown error' }))
    throw new Error(err.detail ?? `HTTP ${res.status}`)
  }
  return res.json()
}

export async function fetchVaultEntry(recordId: string): Promise<VaultEntry> {
  const res = await fetch(`/vault/${recordId}`, { headers: AUTH_HEADERS })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Unknown error' }))
    throw new Error(err.detail ?? `HTTP ${res.status}`)
  }
  return res.json()
}

export async function fetchUserTrend(userId: string): Promise<TrendResponse> {
  const res = await fetch(`/trend/${encodeURIComponent(userId)}`, { headers: AUTH_HEADERS })
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

export interface SessionStateResponse {
  session_status: string
  enforced_actions: { action: string; enforced_at: string }[]
}

export async function fetchSessionState(userId: string): Promise<SessionStateResponse> {
  const res = await fetch(`/session/${encodeURIComponent(userId)}`, { headers: AUTH_HEADERS })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Unknown error' }))
    throw new Error(err.detail ?? `HTTP ${res.status}`)
  }
  return res.json()
}

export async function verifySessionIdentity(userId: string): Promise<SessionStateResponse> {
  const res = await fetch(`/session/${encodeURIComponent(userId)}/verify`, {
    method: 'POST',
    headers: AUTH_HEADERS
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Unknown error' }))
    throw new Error(err.detail ?? `HTTP ${res.status}`)
  }
  return res.json()
}

// ---------------------------------------------------------------------------
// Demo presets
// ---------------------------------------------------------------------------

export interface DemoScenario {
  label: string
  description: string
  tier: string
  getPayload: () => ScoreRequest
}

const rand = (min: number, max: number) => Math.floor(Math.random() * (max - min + 1)) + min

export const DEMO_SCENARIOS: DemoScenario[] = [
  {
    label: 'Critical Threat',
    description: 'Mass data exfiltration — high off-hours activity, USB transfers, suspicious browsing',
    tier: 'Critical',
    getPayload: () => ({
      user: 'CCA0046',
      logon_count: rand(5, 8),
      off_hours_events: rand(8, 15),
      suspicious_url_events: rand(15, 35),
      external_email_count: rand(6, 12),
      unique_pcs: rand(4, 7),
      device_connects: rand(4, 10),
      device_off_hours: rand(3, 8),
      file_events: rand(15, 30),
      removable_file_events: rand(10, 18),
      email_count: rand(25, 40),
      privilege_tier: 'standard',
    }),
  },
  {
    label: 'Slow-Burn Exfiltration',
    description: 'Scenario 2 — moderately elevated activity sustained over many days',
    tier: 'High',
    getPayload: () => ({
      user: 'MAS0025',
      logon_count: 2,
      off_hours_events: rand(0, 1),
      suspicious_url_events: 0,
      external_email_count: rand(5, 7),
      unique_pcs: 1,
      device_connects: 1,
      device_off_hours: 0,
      file_events: rand(1, 2),
      removable_file_events: 0,
      email_count: rand(10, 14),
      privilege_tier: 'standard',
    }),
  },
  {
    label: 'Normal User',
    description: 'Typical low-risk employee — activity within expected baseline',
    tier: 'Low',
    getPayload: () => ({
      user: 'AMR0400',
      logon_count: rand(1, 3),
      off_hours_events: 0,
      suspicious_url_events: 0,
      external_email_count: rand(3, 5),
      unique_pcs: 1,
      device_connects: 0,
      device_off_hours: 0,
      file_events: 0,
      removable_file_events: 0,
      email_count: rand(8, 10),
      privilege_tier: 'standard',
    }),
  },
  {
    label: 'Privileged Admin',
    description: 'Domain admin with anomalous off-hours activity — privilege multiplier amplifies risk',
    tier: 'High',
    getPayload: () => ({
      user: 'SYSADM01',
      logon_count: rand(1, 3),
      off_hours_events: rand(2, 4),
      suspicious_url_events: 0,
      external_email_count: rand(3, 5),
      unique_pcs: rand(1, 3),
      device_connects: rand(1, 2),
      device_off_hours: rand(1, 2),
      file_events: rand(3, 6),
      removable_file_events: 0,
      email_count: rand(8, 12),
      privilege_tier: 'domain_admin',
    }),
  },
]
