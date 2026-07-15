// Reusable glass card container
import type { ReactNode } from 'react'

interface Props {
  children: ReactNode
  className?: string
  glow?: 'red' | 'green' | 'purple' | 'none'
}

const GLOW = {
  red:   'shadow-glow-red border-red-500/20',
  green: 'shadow-glow-green border-emerald-500/20',
  purple:  'shadow-glow-purple border-purple-500/20',
  none:  '',
}

export default function GlassCard({ children, className = '', glow = 'none' }: Props) {
  return (
    <div className={`glass rounded-2xl p-6 ${GLOW[glow]} ${className}`}>
      {children}
    </div>
  )
}
