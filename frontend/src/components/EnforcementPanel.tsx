import { useState } from 'react'
import {
  Shield, AlertTriangle, Lock, UserX, Bell, Key,
  Smartphone, CheckCircle2, Loader2, ShieldCheck
} from 'lucide-react'

// ---------------------------------------------------------------------------
// Per-action metadata: icon, label, and mock confirmation message
// ---------------------------------------------------------------------------
interface ActionMeta {
  icon: React.ReactNode
  label: string
  confirm: string
  severity: 'critical' | 'high' | 'medium' | 'low'
}

const ACTION_META: Record<string, ActionMeta> = {
  require_mfa: {
    icon: <Smartphone className="w-4 h-4" />,
    label: 'Require MFA',
    confirm: '✅ MFA challenge pushed to user device via Microsoft Authenticator',
    severity: 'high',
  },
  restrict_removable_media: {
    icon: <Lock className="w-4 h-4" />,
    label: 'Restrict Removable Media',
    confirm: '✅ USB block policy deployed to endpoint via MDM (Microsoft Intune)',
    severity: 'high',
  },
  alert_soc_immediately: {
    icon: <AlertTriangle className="w-4 h-4" />,
    label: 'Alert SOC',
    confirm: '✅ P1 incident INC-20483 raised in SIEM — SOC analyst assigned',
    severity: 'critical',
  },
  log_enhanced: {
    icon: <Shield className="w-4 h-4" />,
    label: 'Enable Enhanced Logging',
    confirm: '✅ Verbose audit trail enabled — all session events forwarded to SIEM',
    severity: 'medium',
  },
  log_standard: {
    icon: <Shield className="w-4 h-4" />,
    label: 'Standard Logging',
    confirm: '✅ Activity flagged for weekly security review',
    severity: 'low',
  },
  require_step_up_auth: {
    icon: <Key className="w-4 h-4" />,
    label: 'Step-Up Authentication',
    confirm: '✅ Step-up auth challenge sent — user must re-authenticate with hardware token',
    severity: 'high',
  },
  notify_manager: {
    icon: <Bell className="w-4 h-4" />,
    label: 'Notify Manager',
    confirm: '✅ Encrypted notification sent to line manager and HRBP',
    severity: 'medium',
  },
  suspend_admin_session: {
    icon: <UserX className="w-4 h-4" />,
    label: 'Suspend Admin Session',
    confirm: '✅ Active admin session TOKEN-a3f92c terminated — user locked out of privileged context',
    severity: 'critical',
  },
  revoke_domain_admin_token: {
    icon: <UserX className="w-4 h-4" />,
    label: 'Revoke Domain Admin Token',
    confirm: '✅ AD group membership suspended — access token invalidated across all DCs',
    severity: 'critical',
  },
  alert_ciso: {
    icon: <Bell className="w-4 h-4" />,
    label: 'Alert CISO',
    confirm: '✅ CISO notified via encrypted out-of-band channel — executive briefing scheduled',
    severity: 'critical',
  },
  dual_control_required: {
    icon: <ShieldCheck className="w-4 h-4" />,
    label: 'Dual Control Required',
    confirm: '✅ Dual-approval required for all privileged operations — second approver notified',
    severity: 'critical',
  },
  flag_for_pqc_migration: {
    icon: <Lock className="w-4 h-4" />,
    label: 'Flag for PQC Migration',
    confirm: '✅ Data pathways flagged for post-quantum cryptography migration review',
    severity: 'medium',
  },
  quarantine_export: {
    icon: <Lock className="w-4 h-4" />,
    label: 'Quarantine Export',
    confirm: '✅ Exported data quarantined — DLP engine blocked transfer, owner notified',
    severity: 'critical',
  },
  notify_data_owner: {
    icon: <Bell className="w-4 h-4" />,
    label: 'Notify Data Owner',
    confirm: '✅ Data owner alerted — classification review initiated',
    severity: 'medium',
  },
}

const SEVERITY_STYLES: Record<string, string> = {
  critical: 'border-red-500/50 bg-red-100 text-red-900 hover:bg-red-200',
  high:     'border-orange-500/50 bg-orange-100 text-orange-900 hover:bg-orange-200',
  medium:   'border-blue-500/50 bg-blue-100 text-blue-900 hover:bg-blue-200',
  low:      'border-slate-500/50 bg-slate-100 text-slate-900 hover:bg-slate-200',
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------
interface Props {
  actions: string[]
}

export default function EnforcementPanel({ actions }: Props) {
  const [dispatched, setDispatched] = useState<Set<string>>(new Set())
  const [loading, setLoading]       = useState<string | null>(null)

  if (actions.length === 0) {
    return (
      <p className="text-sm text-[#26201b]">No enforcement actions required at this risk level.</p>
    )
  }

  async function dispatch(action: string) {
    if (dispatched.has(action)) return
    setLoading(action)
    // Simulate a ~600ms round-trip to a PAM/SIEM/MDM API
    await new Promise(r => setTimeout(r, 620))
    setDispatched(prev => new Set([...prev, action]))
    setLoading(null)
  }

  const allDispatched = actions.every(a => dispatched.has(a))

  return (
    <div className="space-y-3">
      {/* Action buttons */}
      <div className="space-y-2">
        {actions.map(action => {
          const meta      = ACTION_META[action] ?? {
            icon: <Shield className="w-4 h-4" />,
            label: action.replace(/_/g, ' '),
            confirm: `✅ ${action.replace(/_/g, ' ')} executed`,
            severity: 'medium',
          }
          const isDone    = dispatched.has(action)
          const isLoading = loading === action

          return (
            <div key={action} className="space-y-1.5">
              <button
                onClick={() => dispatch(action)}
                disabled={isDone || isLoading}
                className={`w-full flex items-center justify-between gap-3 px-4 py-3 rounded-xl border text-sm font-medium transition-all duration-200
                  ${isDone
                    ? 'border-emerald-600/40 bg-emerald-100 text-emerald-900 cursor-default'
                    : `${SEVERITY_STYLES[meta.severity]} cursor-pointer active:scale-[0.99]`
                  }`}
              >
                <span className="flex items-center gap-2.5">
                  {isDone
                    ? <CheckCircle2 className="w-4 h-4 text-indigo-400 shrink-0" />
                    : <span className="shrink-0 opacity-80">{meta.icon}</span>
                  }
                  {meta.label}
                </span>
                {isLoading && <Loader2 className="w-3.5 h-3.5 animate-spin opacity-80" />}
                {isDone    && <span className="text-xs font-bold text-emerald-700">Executed</span>}
                {!isDone && !isLoading && (
                  <span className="text-xs opacity-70 font-semibold">Click to dispatch →</span>
                )}
              </button>

              {/* Confirmation message */}
              {isDone && (
                <p className="text-xs text-indigo-400/80 pl-4 font-mono animate-fade-in">
                  {meta.confirm}
                </p>
              )}
            </div>
          )
        })}
      </div>

      {/* All-clear banner */}
      {allDispatched && (
        <div className="flex items-center gap-3 bg-indigo-900/30 border border-[#496b52]/40 rounded-xl px-4 py-3 animate-fade-in">
          <ShieldCheck className="w-5 h-5 text-indigo-400 shrink-0" />
          <div>
            <p className="text-sm font-semibold text-indigo-300">Threat Contained</p>
            <p className="text-xs text-indigo-400/70 mt-0.5">
              All {actions.length} enforcement actions executed successfully
            </p>
          </div>
        </div>
      )}
    </div>
  )
}
