// Clinic Admin audit trail viewer (PLT-5): own tenant, filterable, cursor-
// paginated. Route is permission-gated by admin.view_audit (see App.tsx).
import { useState } from 'react'
import { useTranslation } from 'react-i18next'

import { useV1AuditLogsRetrieve } from '@/api/generated/api'
import { Button } from '@/ui/Button'
import { Input } from '@/ui/Input'

function cursorOf(link: string | null | undefined): string | undefined {
  if (!link) return undefined
  return new URL(link, window.location.origin).searchParams.get('cursor') ?? undefined
}

export function AuditLogPage() {
  const { t, i18n } = useTranslation()
  const [action, setAction] = useState('')
  const [cursor, setCursor] = useState<string | undefined>(undefined)

  const { data, isPending, isError } = useV1AuditLogsRetrieve({
    cursor,
    action: action || undefined,
  })

  const rows = data?.results ?? []
  const nextCursor = cursorOf(data?.next)
  const prevCursor = cursorOf(data?.prev)

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

      <div className="overflow-x-auto rounded-lg border border-border bg-surface">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border text-start text-xs text-text-muted">
              <th className="px-3 py-2 text-start font-medium">{t('audit.when')}</th>
              <th className="px-3 py-2 text-start font-medium">{t('audit.action')}</th>
              <th className="px-3 py-2 text-start font-medium">{t('audit.entity')}</th>
              <th className="px-3 py-2 text-start font-medium">{t('audit.actor')}</th>
              <th className="px-3 py-2 text-start font-medium">{t('audit.ip')}</th>
            </tr>
          </thead>
          <tbody>
            {isPending && (
              <tr>
                <td colSpan={5} className="px-3 py-6 text-center text-text-muted">
                  {t('common.loading')}
                </td>
              </tr>
            )}
            {isError && (
              <tr>
                <td colSpan={5} className="px-3 py-6 text-center text-danger">
                  {t('errors.network')}
                </td>
              </tr>
            )}
            {!isPending && !isError && rows.length === 0 && (
              <tr>
                <td colSpan={5} className="px-3 py-6 text-center text-text-muted">
                  {t('audit.empty')}
                </td>
              </tr>
            )}
            {rows.map((row) => (
              <tr key={row.id} className="h-10 border-b border-border last:border-b-0">
                <td className="whitespace-nowrap px-3 py-1.5 text-text-muted">
                  {new Date(row.created_at).toLocaleString(i18n.language)}
                </td>
                <td className="px-3 py-1.5 font-medium">{row.action}</td>
                <td className="px-3 py-1.5 text-text-muted" dir="ltr">
                  {row.entity_type || '—'}
                </td>
                <td className="px-3 py-1.5">{row.actor_username ?? t('audit.system')}</td>
                <td className="px-3 py-1.5 text-text-muted" dir="ltr">
                  {row.ip ?? '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="flex gap-2">
        <Button
          variant="outline"
          size="sm"
          disabled={!prevCursor && cursor === undefined}
          onClick={() => setCursor(prevCursor)}
        >
          {t('common.prev')}
        </Button>
        <Button
          variant="outline"
          size="sm"
          disabled={!nextCursor}
          onClick={() => setCursor(nextCursor)}
        >
          {t('common.next')}
        </Button>
      </div>
    </section>
  )
}
