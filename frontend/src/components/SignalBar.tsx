// Visual z-score bar for one signal returned by /score → top_signals
import type { TopSignal } from '../api'

export default function SignalBar({ signal }: { signal: TopSignal }) {
  const z        = signal.zscore
  const absZ     = Math.abs(z)
  const isDrop   = z < 0
  const barPct   = Math.min(absZ / 6, 1) * 100  // cap at 6σ = 100%
  const colour   = absZ > 3
    ? isDrop ? 'bg-orange-500' : 'bg-red-500'
    : absZ > 1.5
    ? 'bg-yellow-500'
    : 'bg-indigo-500'

  return (
    <div className="flex items-start gap-3 py-1.5">
      {/* Z-score label */}
      <span className={`text-xs font-mono w-14 shrink-0 text-right pt-0.5 ${
        isDrop ? 'text-orange-400' : 'text-red-400'
      }`}>
        {z > 0 ? '+' : ''}{z.toFixed(1)}σ
      </span>

      {/* Bar + label */}
      <div className="flex-1 min-w-0">
        <div className="h-1.5 bg-slate-700 rounded-full overflow-hidden mb-1">
          <div
            className={`h-full rounded-full transition-all duration-500 ${colour}`}
            style={{ width: `${barPct}%` }}
          />
        </div>
        <p className="text-xs text-[#26201b] truncate">{signal.label}</p>
      </div>
    </div>
  )
}
