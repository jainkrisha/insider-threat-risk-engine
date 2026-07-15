type Tier = 'Low' | 'Medium' | 'High' | 'Critical'

const STYLES: Record<Tier, string> = {
  Low:      'bg-emerald-500/15 text-emerald-400 border-emerald-500/30',
  Medium:   'bg-yellow-500/15  text-yellow-400  border-yellow-500/30',
  High:     'bg-orange-500/15  text-orange-400  border-orange-500/30',
  Critical: 'bg-red-500/15     text-red-400     border-red-500/30',
}

export default function TierBadge({ tier }: { tier: Tier }) {
  return (
    <span className={`inline-flex px-4 py-1 rounded-full text-sm font-semibold uppercase tracking-wider border ${STYLES[tier]}`}>
      {tier}
    </span>
  )
}
