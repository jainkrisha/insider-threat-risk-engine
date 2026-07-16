import { Lock } from 'lucide-react'
import { Link } from 'react-router-dom'

interface Props {
  recordId: string
  onViewAudit?: () => void
}

export default function AuditBadge({ recordId, onViewAudit }: Props) {
  return (
    <div className="flex items-start gap-3 bg-[#dcceb4] border border-[#cab593] rounded-xl p-4 animate-fade-in shadow-sm">
      <div className="mt-0.5 w-8 h-8 rounded-full bg-[#496b52]/10 border border-[#496b52]/20 flex items-center justify-center shrink-0">
        <Lock className="w-4 h-4 text-[#496b52]" />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-semibold text-[#26201b]">
          Sealed in tamper-proof audit log
        </p>
        <p className="text-xs text-[#544c41] mt-0.5">
          Record ID:{' '}
          <code className="font-mono text-[#26201b] font-semibold break-all">{recordId}</code>
        </p>
        <p className="text-xs text-[#496b52] mt-1">
          Encrypted with hybrid X25519 + ML-KEM-768 —{' '}
          <Link to="/features" className="underline underline-offset-2 hover:text-[#26201b] font-medium transition-colors">
            learn more
          </Link>
        </p>
        {onViewAudit && (
          <button
            onClick={onViewAudit}
            className="mt-2 text-xs text-[#544c41] hover:text-[#26201b] font-semibold underline underline-offset-2 transition-colors"
          >
            Verify decryption →
          </button>
        )}
      </div>
    </div>
  )
}
