import { Languages } from 'lucide-react'
import { useTranslation } from 'react-i18next'

import { resolvedLanguage } from '@/lib/i18n'
import { Button } from '@/ui/Button'

export function LanguageToggle() {
  const { i18n } = useTranslation()
  const next = resolvedLanguage() === 'ar' ? 'en' : 'ar'
  return (
    <Button variant="ghost" size="sm" onClick={() => i18n.changeLanguage(next)}>
      <Languages className="size-4" aria-hidden />
      {next === 'ar' ? 'العربية' : 'English'}
    </Button>
  )
}
