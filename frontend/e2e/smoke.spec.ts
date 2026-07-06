import { expect, test } from '@playwright/test'

// Placeholder smoke — replaced by the login-in-en-and-ar smoke in M0
// deliverable 9 once the login page (deliverable 7) exists.
test('app shell loads', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByRole('heading')).toBeVisible()
})
