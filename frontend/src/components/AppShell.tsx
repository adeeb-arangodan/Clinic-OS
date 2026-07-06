// Role-first shell (docs/03 §5.1): sidebar entries appear only when the user
// holds the permission / feature — the server enforces regardless (rule 9).
import { Home, LogOut, ScrollText } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { NavLink, Outlet, useNavigate } from 'react-router-dom'

import { LanguageToggle } from '@/components/LanguageToggle'
import { useAuth } from '@/features/auth/AuthContext'
import { cn } from '@/lib/utils'
import { Button } from '@/ui/Button'

function navLinkClass({ isActive }: { isActive: boolean }) {
  return cn(
    'flex items-center gap-2 rounded-md px-3 py-2 text-sm',
    isActive ? 'bg-primary text-primary-foreground' : 'text-text-muted hover:bg-bg hover:text-text',
  )
}

export function AppShell() {
  const { t } = useTranslation()
  const { user, logout, hasPermission } = useAuth()
  const navigate = useNavigate()

  const onLogout = async () => {
    await logout()
    navigate('/login', { replace: true })
  }

  return (
    <div className="flex min-h-screen">
      <aside className="flex w-60 flex-col border-e border-border bg-surface">
        <div className="flex h-14 items-center border-b border-border px-4">
          <span className="text-lg font-semibold text-primary">{t('app.name')}</span>
        </div>
        <nav aria-label={t('nav.main')} className="flex flex-1 flex-col gap-1 p-3">
          <NavLink to="/" end className={navLinkClass}>
            <Home className="size-4" aria-hidden />
            {t('nav.home')}
          </NavLink>
          {hasPermission('admin.view_audit') && (
            <NavLink to="/audit-logs" className={navLinkClass}>
              <ScrollText className="size-4" aria-hidden />
              {t('nav.auditLog')}
            </NavLink>
          )}
        </nav>
      </aside>
      <div className="flex flex-1 flex-col">
        <header className="flex h-14 items-center justify-between border-b border-border bg-surface px-4">
          <span className="text-sm text-text-muted">
            {user?.first_name || user?.username}
          </span>
          <div className="flex items-center gap-2">
            <LanguageToggle />
            <Button variant="ghost" size="sm" onClick={onLogout}>
              <LogOut className="size-4" aria-hidden />
              {t('common.logout')}
            </Button>
          </div>
        </header>
        <main className="flex-1 p-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
