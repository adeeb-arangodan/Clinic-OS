// shadcn-style wrapper over Radix Select (docs/02 §7 design system), themed
// with the SehaERP tokens and RTL-safe (logical properties + dir-aware icons).
import * as SelectPrimitive from '@radix-ui/react-select'
import { Check, ChevronDown } from 'lucide-react'
import type { ComponentPropsWithoutRef } from 'react'

import { cn } from '@/lib/utils'

export const Select = SelectPrimitive.Root
export const SelectValue = SelectPrimitive.Value

export function SelectTrigger({
  className,
  children,
  ...props
}: ComponentPropsWithoutRef<typeof SelectPrimitive.Trigger>) {
  return (
    <SelectPrimitive.Trigger
      className={cn(
        'flex h-9 w-full items-center justify-between gap-2 rounded-md border border-border bg-surface px-3 text-sm text-text focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-primary disabled:cursor-not-allowed disabled:opacity-50 [&>span]:truncate',
        className,
      )}
      {...props}
    >
      {children}
      <SelectPrimitive.Icon asChild>
        <ChevronDown className="size-4 shrink-0 text-text-muted" aria-hidden />
      </SelectPrimitive.Icon>
    </SelectPrimitive.Trigger>
  )
}

export function SelectContent({
  className,
  children,
  ...props
}: ComponentPropsWithoutRef<typeof SelectPrimitive.Content>) {
  return (
    <SelectPrimitive.Portal>
      <SelectPrimitive.Content
        position="popper"
        sideOffset={4}
        className={cn(
          'z-50 min-w-(--radix-select-trigger-width) overflow-hidden rounded-md border border-border bg-surface shadow-md',
          className,
        )}
        {...props}
      >
        <SelectPrimitive.Viewport className="p-1">{children}</SelectPrimitive.Viewport>
      </SelectPrimitive.Content>
    </SelectPrimitive.Portal>
  )
}

export function SelectItem({
  className,
  children,
  ...props
}: ComponentPropsWithoutRef<typeof SelectPrimitive.Item>) {
  return (
    <SelectPrimitive.Item
      className={cn(
        'relative flex cursor-default select-none items-center rounded-sm py-1.5 ps-8 pe-2 text-sm text-text outline-none data-[highlighted]:bg-bg data-disabled:pointer-events-none data-disabled:opacity-50',
        className,
      )}
      {...props}
    >
      <span className="absolute start-2 flex size-4 items-center justify-center">
        <SelectPrimitive.ItemIndicator>
          <Check className="size-4 text-primary" aria-hidden />
        </SelectPrimitive.ItemIndicator>
      </span>
      <SelectPrimitive.ItemText>{children}</SelectPrimitive.ItemText>
    </SelectPrimitive.Item>
  )
}
