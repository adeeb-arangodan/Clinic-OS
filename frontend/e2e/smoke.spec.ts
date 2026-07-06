import { expect, test } from '@playwright/test'

import ar from '../src/locales/ar.json' with { type: 'json' }
import en from '../src/locales/en.json' with { type: 'json' }

// M0 acceptance smoke (deliverable 9): full-stack login in both locales.
// Requires the backend on :8000 with `manage.py seed_demo` applied; the
// chromium-en / chromium-ar projects drive the locale via the browser.

test('login with demo Clinic Admin and reach the audit log', async ({ page }, testInfo) => {
  const isArabic = testInfo.project.name.endsWith('-ar')
  const t = isArabic ? ar : en

  await page.goto('/')
  await expect(page).toHaveURL(/\/login$/)
  await expect(page.getByRole('heading', { name: t.app.name })).toBeVisible()
  expect(await page.evaluate(() => document.documentElement.dir)).toBe(isArabic ? 'rtl' : 'ltr')

  await page.getByLabel(t.login.username).fill('demo.clinic-admin')
  await page.getByLabel(t.login.password).fill('SehaDemo-1234')
  await page.getByRole('button', { name: t.login.submit }).click()

  const welcome = t.home.welcome.replace('{{name}}', 'Clinic Admin')
  await expect(page.getByText(welcome)).toBeVisible()

  // Permission-gated nav + server data end-to-end: the audit page must show
  // this very login recorded by the audit middleware.
  await page.getByRole('link', { name: t.nav.auditLog }).click()
  await expect(page.getByText('auth.login').first()).toBeVisible()
})

test('wrong password shows the bilingual error envelope', async ({ page }, testInfo) => {
  const isArabic = testInfo.project.name.endsWith('-ar')
  const t = isArabic ? ar : en

  await page.goto('/login')
  await page.getByLabel(t.login.username).fill('demo.clinic-admin')
  await page.getByLabel(t.login.password).fill('wrong-password-123')
  await page.getByRole('button', { name: t.login.submit }).click()

  await expect(page.getByRole('alert')).toContainText(
    isArabic ? 'اسم المستخدم أو كلمة المرور غير صحيحة.' : 'Invalid username or password.',
  )
})
