import { useState, useEffect } from 'react'
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
  sessionStatus?: string
  onVerifyIdentity?: () => void
}

export default function EnforcementPanel({ actions, sessionStatus, onVerifyIdentity }: Props) {
  const [visibleActions, setVisibleActions] = useState<Set<string>>(new Set())

  // Staggered animation for auto-enforced actions
  useEffect(() => {
    if (actions.length === 0) return
    
    // Reset state on new actions list
    setVisibleActions(new Set())
    
    actions.forEach((action, i) => {
      setTimeout(() => {
        setVisibleActions(prev => new Set([...prev, action]))
      }, (i + 1) * 400) // 400ms stagger per item
    })
  }, [actions])

  if (actions.length === 0) {
    return (
      <p className="text-sm text-[#26201b]">No enforcement actions required at this risk level.</p>
    )
  }

  const allVisible = actions.every(a => visibleActions.has(a))
  const isStepUp = sessionStatus === 'step_up_required'

  return (
    <div className="space-y-3">
      {/* Session suspended alert (Only for step_up_required do we show the Verify button) */}
      {isStepUp && onVerifyIdentity && (
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 bg-orange-50 border border-orange-200 rounded-xl p-4 animate-fade-in">
          <div>
            <p className="text-sm font-semibold text-orange-900">Session Step-Up Required</p>
            <p className="text-xs text-orange-800/80 mt-0.5">
              Access is restricted. User identity must be verified to continue.
            </p>
          </div>
          <button
            onClick={onVerifyIdentity}
            className="px-4 py-2 bg-orange-600 text-white text-sm font-medium rounded-lg shadow hover:bg-orange-700 transition-colors shrink-0"
          >
            Verify Identity
          </button>
        </div>
      )}

      {/* Action list */}
      <div className="space-y-2">
        {actions.map((action, idx) => {
          const meta      = ACTION_META[action] ?? {
            icon: <Shield className="w-4 h-4" />,
            label: action.replace(/_/g, ' '),
            confirm: `✅ ${action.replace(/_/g, ' ')} executed`,
            severity: 'medium',
          }
          const isVisible = visibleActions.has(action)

          return (
            <div key={action} className="space-y-1.5 overflow-hidden">
              {isVisible ? (
                <div className="animate-fade-in-up">
                  <div className={`w-full flex items-center justify-between gap-3 px-4 py-3 rounded-xl border text-sm font-medium border-emerald-600/40 bg-emerald-100 text-emerald-900`}>
                    <span className="flex items-center gap-2.5">
                      <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                      {meta.label}
                    </span>
                    <span className="text-xs font-bold text-emerald-700">Enforced automatically</span>
                  </div>
                  <p className="text-xs text-emerald-600/80 pl-4 mt-1 font-mono">
                    {meta.confirm}
                  </p>
                </div>
              ) : (
                <div className="w-full flex items-center justify-between gap-3 px-4 py-3 rounded-xl border border-slate-200 bg-slate-50/50 text-slate-400 opacity-50">
                  <span className="flex items-center gap-2.5">
                    <Loader2 className="w-4 h-4 animate-spin shrink-0" />
                    {meta.label}
                  </span>
                  <span className="text-xs font-semibold">Enforcing...</span>
                </div>
              )}
            </div>
          )
        })}
      </div>

      {/* All-clear banner */}
      {allVisible && (
        <div className="flex items-center gap-3 bg-indigo-900/30 border border-[#496b52]/40 rounded-xl px-4 py-3 animate-fade-in">
          <ShieldCheck className="w-5 h-5 text-indigo-400 shrink-0" />
          <div>
            <p className="text-sm font-semibold text-indigo-300">Threat Contained</p>
            <p className="text-xs text-indigo-400/70 mt-0.5">
              All {actions.length} enforcement actions executed automatically
            </p>
          </div>
        </div>
      )}
    </div>
  )
}
