// Reusable glass card container
import type { ReactNode } from 'react'

interface Props {
  children: ReactNode
  className?: string
  glow?: 'red' | 'green' | 'yellow' | 'none'
}

const GLOW = {
  red:   'shadow-glow-red border-red-500/20',
  green: 'shadow-glow-green border-[#496b52]/20',
  yellow:  'shadow-glow-teal border-[#92402d]/20',
  none:  '',
}

export default function GlassCard({ children, className = '', glow = 'none' }: Props) {
  return (
    <div className={`glass rounded-2xl p-6 ${GLOW[glow]} ${className}`}>
      {children}
    </div>
  )
}
