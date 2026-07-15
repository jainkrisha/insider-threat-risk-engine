import { Lock } from 'lucide-react'
import { Link } from 'react-router-dom'

interface Props {
  recordId: string
  onViewAudit?: () => void
}

export default function AuditBadge({ recordId, onViewAudit }: Props) {
  return (
    <div className="flex items-start gap-3 bg-indigo-950/50 border border-indigo-500/25 rounded-xl p-4 animate-fade-in">
      <div className="mt-0.5 w-8 h-8 rounded-full bg-indigo-500/20 flex items-center justify-center shrink-0">
        <Lock className="w-4 h-4 text-indigo-400" />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-indigo-200">
          Sealed in tamper-proof audit log
        </p>
        <p className="text-xs text-indigo-400 mt-0.5">
          Record ID:{' '}
          <code className="font-mono text-indigo-300 break-all">{recordId}</code>
        </p>
        <p className="text-xs text-indigo-500 mt-1">
          Encrypted with hybrid X25519 + ML-KEM-768 —{' '}
          <Link to="/features" className="underline underline-offset-2 hover:text-indigo-300">
            learn more
          </Link>
        </p>
        {onViewAudit && (
          <button
            onClick={onViewAudit}
            className="mt-2 text-xs text-indigo-300 hover:text-white underline underline-offset-2"
          >
            Verify decryption →
          </button>
        )}
      </div>
    </div>
  )
}
