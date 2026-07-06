import { useTranslation } from 'react-i18next'

import { useAuth } from '@/features/auth/AuthContext'

export function HomePage() {
  const { t } = useTranslation()
  const { user } = useAuth()

  return (
    <section className="flex flex-col gap-2">
      <h1 className="text-xl font-semibold">
        {t('home.welcome', { name: user?.first_name || user?.username })}
      </h1>
      <p className="text-sm text-text-muted">{t('home.hint')}</p>
    </section>
  )
}
