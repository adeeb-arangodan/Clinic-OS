import { useTranslation } from 'react-i18next'
import { Navigate, Outlet, useLocation } from 'react-router-dom'

import { useAuth } from '@/features/auth/AuthContext'

export function RequireAuth() {
  const { user, status } = useAuth()
  const location = useLocation()
  const { t } = useTranslation()

  if (status === 'restoring') {
    return (
      <div className="flex min-h-screen items-center justify-center text-text-muted">
        {t('common.loading')}
      </div>
    )
  }
  if (!user) return <Navigate to="/login" replace state={{ from: location }} />
  return <Outlet />
}

export function RequirePermission({ permission }: { permission: string }) {
  const { hasPermission } = useAuth()
  return hasPermission(permission) ? <Outlet /> : <Navigate to="/" replace />
}
