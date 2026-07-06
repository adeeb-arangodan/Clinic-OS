import type { InputHTMLAttributes } from 'react'

import { cn } from '@/lib/utils'

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  invalid?: boolean
}

export function Input({ className, invalid, ...props }: InputProps) {
  return (
    <input
      aria-invalid={invalid || undefined}
      className={cn(
        'h-9 w-full rounded-md border border-border bg-surface px-3 text-sm text-text placeholder:text-text-muted focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-primary',
        invalid && 'border-danger focus-visible:outline-danger',
        className,
      )}
      {...props}
    />
  )
}
