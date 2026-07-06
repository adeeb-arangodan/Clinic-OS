// Generic worklist table (docs/03 §5.2: compact 40px rows, tabular figures)
// with cursor-based server pagination matching the {results, next, prev}
// envelope (docs/03 §3). Purely presentational — data fetching stays in the
// feature's TanStack Query hooks.
import type { ReactNode } from 'react'
import { useTranslation } from 'react-i18next'

import { cn } from '@/lib/utils'
import { Button } from '@/ui/Button'

export interface DataTableColumn<Row> {
  key: string
  header: ReactNode
  cell: (row: Row) => ReactNode
  className?: string
}

export interface DataTablePagination {
  hasPrev: boolean
  hasNext: boolean
  onPrev: () => void
  onNext: () => void
}

interface DataTableProps<Row> {
  columns: DataTableColumn<Row>[]
  rows: Row[]
  rowKey: (row: Row) => string
  isPending?: boolean
  isError?: boolean
  emptyLabel?: ReactNode
  pagination?: DataTablePagination
}

export function DataTable<Row>({
  columns,
  rows,
  rowKey,
  isPending = false,
  isError = false,
  emptyLabel,
  pagination,
}: DataTableProps<Row>) {
  const { t } = useTranslation()

  let body: ReactNode
  if (isPending) {
    body = <PlaceholderRow span={columns.length}>{t('common.loading')}</PlaceholderRow>
  } else if (isError) {
    body = (
      <PlaceholderRow span={columns.length} className="text-danger">
        {t('errors.network')}
      </PlaceholderRow>
    )
  } else if (rows.length === 0) {
    body = <PlaceholderRow span={columns.length}>{emptyLabel ?? t('common.empty')}</PlaceholderRow>
  } else {
    body = rows.map((row) => (
      <tr key={rowKey(row)} className="h-10 border-b border-border last:border-b-0">
        {columns.map((column) => (
          <td key={column.key} className={cn('px-3 py-1.5', column.className)}>
            {column.cell(row)}
          </td>
        ))}
      </tr>
    ))
  }

  return (
    <div className="flex flex-col gap-3">
      <div className="overflow-x-auto rounded-lg border border-border bg-surface">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border text-xs text-text-muted">
              {columns.map((column) => (
                <th
                  key={column.key}
                  className={cn('px-3 py-2 text-start font-medium', column.className)}
                >
                  {column.header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>{body}</tbody>
        </table>
      </div>
      {pagination && (
        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            disabled={!pagination.hasPrev}
            onClick={pagination.onPrev}
          >
            {t('common.prev')}
          </Button>
          <Button
            variant="outline"
            size="sm"
            disabled={!pagination.hasNext}
            onClick={pagination.onNext}
          >
            {t('common.next')}
          </Button>
        </div>
      )}
    </div>
  )
}

function PlaceholderRow({
  span,
  className,
  children,
}: {
  span: number
  className?: string
  children: ReactNode
}) {
  return (
    <tr>
      <td colSpan={span} className={cn('px-3 py-6 text-center text-text-muted', className)}>
        {children}
      </td>
    </tr>
  )
}
