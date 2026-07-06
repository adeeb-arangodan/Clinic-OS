// "Status is always visible" (docs/03 §5.1): colored chip with plain-language
// state. Kinds map to the insurance chip palette in docs/03 §5.2; domain code
// maps its statuses (queued/processing/success/… ) onto a kind.
import type { ReactNode } from 'react'

import { cn } from '@/lib/utils'

const chipKinds = {
  eligible: 'bg-chip-eligible-bg text-chip-eligible-text',
  pending: 'bg-chip-pending-bg text-chip-pending-text',
  rejected: 'bg-chip-rejected-bg text-chip-rejected-text',
  cash: 'bg-chip-cash-bg text-chip-cash-text',
} as const

export type StatusChipKind = keyof typeof chipKinds

export function StatusChip({
  kind,
  className,
  children,
}: {
  kind: StatusChipKind
  className?: string
  children: ReactNode
}) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium',
        chipKinds[kind],
        className,
      )}
    >
      {children}
    </span>
  )
}
