// Clinic Admin audit trail viewer (PLT-5): own tenant, filterable, cursor-
// paginated. Route is permission-gated by admin.view_audit (see App.tsx).
import { useState } from 'react'
import { useTranslation } from 'react-i18next'

import { useV1AuditLogsRetrieve } from '@/api/generated/api'
import type { AuditLog } from '@/api/generated/model'
import { DataTable, type DataTableColumn } from '@/ui/DataTable'
import { DualDate } from '@/ui/DualDate'
import { Input } from '@/ui/Input'

function cursorOf(link: string | null | undefined): string | undefined {
  if (!link) return undefined
  return new URL(link, window.location.origin).searchParams.get('cursor') ?? undefined
}

export function AuditLogPage() {
  const { t } = useTranslation()
  const [action, setAction] = useState('')
  const [cursor, setCursor] = useState<string | undefined>(undefined)

  const { data, isPending, isError } = useV1AuditLogsRetrieve({
    cursor,
    action: action || undefined,
  })

  const nextCursor = cursorOf(data?.next)
  const prevCursor = cursorOf(data?.prev)

  const columns: DataTableColumn<AuditLog>[] = [
    {
      key: 'when',
      header: t('audit.when'),
      className: 'whitespace-nowrap',
      cell: (row) => <DualDate date={row.created_at} showTime />,
    },
    { key: 'action', header: t('audit.action'), cell: (row) => <b>{row.action}</b> },
    {
      key: 'entity',
      header: t('audit.entity'),
      className: 'text-text-muted',
      cell: (row) => <span dir="ltr">{row.entity_type || '—'}</span>,
    },
    {
      key: 'actor',
      header: t('audit.actor'),
      cell: (row) => row.actor_username ?? t('audit.system'),
    },
    {
      key: 'ip',
      header: t('audit.ip'),
      className: 'text-text-muted',
      cell: (row) => <span dir="ltr">{row.ip ?? '—'}</span>,
    },
  ]

  return (
    <section className="flex flex-col gap-4">
      <div className="flex items-center justify-between gap-4">
        <h1 className="text-xl font-semibold">{t('audit.title')}</h1>
        <Input
          className="max-w-56"
          placeholder={t('audit.filterAction')}
          value={action}
          onChange={(event) => {
            setAction(event.target.value)
            setCursor(undefined)
          }}
        />
      </div>
      <DataTable
        columns={columns}
        rows={data?.results ?? []}
        rowKey={(row) => row.id}
        isPending={isPending}
        isError={isError}
        emptyLabel={t('audit.empty')}
        pagination={{
          hasPrev: !!prevCursor || cursor !== undefined,
          hasNext: !!nextCursor,
          onPrev: () => setCursor(prevCursor),
          onNext: () => setCursor(nextCursor),
        }}
      />
    </section>
  )
}
