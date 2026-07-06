// Gregorian primary with Hijri (Umm al-Qura) secondary (PLT-7, docs/02 §7).
// Storage is always Gregorian UTC; this is display-only conversion via Intl —
// no calendar library needed.
import { useTranslation } from 'react-i18next'

export function DualDate({
  date,
  showTime = false,
  showHijri = true,
}: {
  date: string | Date
  showTime?: boolean
  showHijri?: boolean
}) {
  const { i18n } = useTranslation()
  const value = typeof date === 'string' ? new Date(date) : date

  const gregorian = new Intl.DateTimeFormat(i18n.language, {
    dateStyle: 'medium',
    ...(showTime ? { timeStyle: 'short' } : {}),
  }).format(value)

  const hijri = showHijri
    ? new Intl.DateTimeFormat(`${i18n.language}-u-ca-islamic-umalqura`, {
        dateStyle: 'medium',
      }).format(value)
    : null

  return (
    <span className="inline-flex flex-col leading-tight">
      <span>{gregorian}</span>
      {hijri && <span className="text-xs text-text-muted">{hijri}</span>}
    </span>
  )
}
