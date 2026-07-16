type Tier = 'Low' | 'Medium' | 'High' | 'Critical'

const STYLES: Record<Tier, string> = {
  Low:      'bg-[#496b52]/15 text-indigo-400 border-[#496b52]/30',
  Medium:   'bg-[#92402d]/15  text-pink-400  border-[#92402d]/30',
  High:     'bg-[#92402d]/15  text-purple-400  border-[#92402d]/30',
  Critical: 'bg-red-500/15     text-red-400     border-red-500/30',
}

export default function TierBadge({ tier }: { tier: Tier }) {
  return (
    <span className={`inline-flex px-4 py-1 rounded-full text-sm font-semibold uppercase tracking-wider border ${STYLES[tier]}`}>
      {tier}
    </span>
  )
}
