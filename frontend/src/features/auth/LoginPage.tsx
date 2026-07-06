import { zodResolver } from '@hookform/resolvers/zod'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { useTranslation } from 'react-i18next'
import { Navigate, useLocation, useNavigate } from 'react-router-dom'
import { z } from 'zod'

import { ApiError } from '@/api/http'
import { useAuth } from '@/features/auth/AuthContext'
import { resolvedLanguage } from '@/lib/i18n'
import { LanguageToggle } from '@/components/LanguageToggle'
import { Button } from '@/ui/Button'
import { Input } from '@/ui/Input'

const loginSchema = z.object({
  username: z.string().min(1, 'login.required'),
  password: z.string().min(1, 'login.required'),
})

type LoginForm = z.infer<typeof loginSchema>

export function LoginPage() {
  const { t } = useTranslation()
  const { user, login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [serverError, setServerError] = useState<string | null>(null)
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginForm>({ resolver: zodResolver(loginSchema) })

  if (user) return <Navigate to="/" replace />

  const onSubmit = async (values: LoginForm) => {
    setServerError(null)
    try {
      await login(values.username, values.password)
      const from = (location.state as { from?: { pathname: string } } | null)?.from?.pathname
      navigate(from ?? '/', { replace: true })
    } catch (error) {
      if (error instanceof ApiError) {
        setServerError(
          resolvedLanguage() === 'ar' ? error.envelope.message_ar : error.envelope.message_en,
        )
      } else {
        setServerError(t('errors.network'))
      }
    }
  }

  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-6 p-4">
      <div className="absolute top-4 end-4">
        <LanguageToggle />
      </div>
      <div className="flex flex-col items-center gap-1">
        <h1 className="text-2xl font-semibold text-primary">{t('app.name')}</h1>
        <p className="text-sm text-text-muted">{t('app.tagline')}</p>
      </div>
      <form
        onSubmit={handleSubmit(onSubmit)}
        noValidate
        className="w-full max-w-sm rounded-lg border border-border bg-surface p-6 shadow-sm"
      >
        <h2 className="mb-4 text-lg font-semibold">{t('login.title')}</h2>
        {serverError && (
          <p role="alert" className="mb-4 rounded-md bg-chip-rejected-bg px-3 py-2 text-sm text-chip-rejected-text">
            {serverError}
          </p>
        )}
        <div className="mb-4 flex flex-col gap-1.5">
          <label htmlFor="username" className="text-sm font-medium">
            {t('login.username')}
          </label>
          <Input
            id="username"
            autoComplete="username"
            invalid={!!errors.username}
            {...register('username')}
          />
          {errors.username && (
            <p className="text-xs text-danger">{t(errors.username.message ?? '')}</p>
          )}
        </div>
        <div className="mb-6 flex flex-col gap-1.5">
          <label htmlFor="password" className="text-sm font-medium">
            {t('login.password')}
          </label>
          <Input
            id="password"
            type="password"
            autoComplete="current-password"
            invalid={!!errors.password}
            {...register('password')}
          />
          {errors.password && (
            <p className="text-xs text-danger">{t(errors.password.message ?? '')}</p>
          )}
        </div>
        <Button type="submit" className="w-full" disabled={isSubmitting}>
          {isSubmitting ? t('common.loading') : t('login.submit')}
        </Button>
      </form>
    </main>
  )
}
