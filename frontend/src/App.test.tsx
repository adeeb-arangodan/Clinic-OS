import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'

import App from '@/App'
import i18n from '@/lib/i18n'

function renderApp() {
  return render(
    <QueryClientProvider client={new QueryClient()}>
      <MemoryRouter>
        <App />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('App shell', () => {
  it('renders the app name in English', async () => {
    await i18n.changeLanguage('en')
    renderApp()
    expect(screen.getByRole('heading', { name: 'SehaERP' })).toBeInTheDocument()
    expect(document.documentElement.dir).toBe('ltr')
  })

  it('renders in Arabic with RTL direction', async () => {
    await i18n.changeLanguage('ar')
    renderApp()
    expect(screen.getByRole('heading', { name: 'صحة ERP' })).toBeInTheDocument()
    expect(document.documentElement.dir).toBe('rtl')
  })
})
