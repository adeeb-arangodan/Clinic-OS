import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import App from '@/App'
import { setAccessToken } from '@/api/auth-token'
import { AuthProvider } from '@/features/auth/AuthContext'
import i18n from '@/lib/i18n'

const NOT_AUTHENTICATED = {
  code: 'auth.token_invalid',
  message_en: 'Your session has expired or is invalid. Please sign in again.',
  message_ar: 'انتهت جلستك أو أنها غير صالحة. الرجاء تسجيل الدخول مرة أخرى.',
  field_errors: {},
}

const INVALID_CREDENTIALS = {
  code: 'auth.invalid_credentials',
  message_en: 'Invalid username or password.',
  message_ar: 'اسم المستخدم أو كلمة المرور غير صحيحة.',
  field_errors: {},
}

const ADMIN_USER = {
  id: '11111111-1111-1111-1111-111111111111',
  username: 'demo.clinic-admin',
  first_name: 'Clinic Admin',
  last_name: 'Demo',
  tenant: 'demo',
  permissions: ['admin.view_audit', 'reports.view'],
  features: ['reception', 'billing'],
}

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

function stubFetch(handler: (url: string) => Response) {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: RequestInfo | URL) => handler(String(url))),
  )
}

function stubUnauthenticated(loginResponse?: Response) {
  stubFetch((url) => {
    if (url.includes('/auth/refresh/')) return jsonResponse(401, NOT_AUTHENTICATED)
    if (url.includes('/auth/login/')) return loginResponse ?? jsonResponse(401, INVALID_CREDENTIALS)
    if (url.includes('/audit-logs/')) return jsonResponse(200, { results: [], next: null, prev: null })
    return jsonResponse(404, NOT_AUTHENTICATED)
  })
}

function renderApp() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <MemoryRouter>
          <App />
        </MemoryRouter>
      </AuthProvider>
    </QueryClientProvider>,
  )
}

beforeEach(async () => {
  setAccessToken(null)
  await i18n.changeLanguage('en')
})

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('App shell', () => {
  it('shows the login page in English when unauthenticated', async () => {
    stubUnauthenticated()
    renderApp()

    expect(await screen.findByRole('heading', { name: 'SehaERP' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Sign in' })).toBeInTheDocument()
    expect(document.documentElement.dir).toBe('ltr')
  })

  it('shows the login page in Arabic with RTL direction', async () => {
    await i18n.changeLanguage('ar')
    stubUnauthenticated()
    renderApp()

    expect(await screen.findByRole('heading', { name: 'صحة ERP' })).toBeInTheDocument()
    expect(document.documentElement.dir).toBe('rtl')
  })

  it('validates required fields before submitting', async () => {
    stubUnauthenticated()
    renderApp()
    await screen.findByRole('button', { name: 'Sign in' })

    await userEvent.click(screen.getByRole('button', { name: 'Sign in' }))

    expect(await screen.findAllByText('This field is required')).toHaveLength(2)
  })

  it('shows the server error envelope message on bad credentials', async () => {
    stubUnauthenticated()
    renderApp()
    await screen.findByRole('button', { name: 'Sign in' })

    await userEvent.type(screen.getByLabelText('Username or email'), 'ghost')
    await userEvent.type(screen.getByLabelText('Password'), 'wrong-password')
    await userEvent.click(screen.getByRole('button', { name: 'Sign in' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('Invalid username or password.')
  })

  it('logs in and shows the shell with permission-gated navigation', async () => {
    stubUnauthenticated(jsonResponse(200, { access: 'test-access-token', user: ADMIN_USER }))
    renderApp()
    await screen.findByRole('button', { name: 'Sign in' })

    await userEvent.type(screen.getByLabelText('Username or email'), 'demo.clinic-admin')
    await userEvent.type(screen.getByLabelText('Password'), 'SehaDemo-1234')
    await userEvent.click(screen.getByRole('button', { name: 'Sign in' }))

    expect(await screen.findByText('Welcome, Clinic Admin')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Audit log' })).toBeInTheDocument()
  })

  it('hides permission-gated navigation from users without the permission', async () => {
    stubUnauthenticated(
      jsonResponse(200, {
        access: 'test-access-token',
        user: { ...ADMIN_USER, permissions: ['reception.view'] },
      }),
    )
    renderApp()
    await screen.findByRole('button', { name: 'Sign in' })

    await userEvent.type(screen.getByLabelText('Username or email'), 'demo.receptionist')
    await userEvent.type(screen.getByLabelText('Password'), 'SehaDemo-1234')
    await userEvent.click(screen.getByRole('button', { name: 'Sign in' }))

    await screen.findByText('Welcome, Clinic Admin')
    expect(screen.queryByRole('link', { name: 'Audit log' })).not.toBeInTheDocument()
  })
})
