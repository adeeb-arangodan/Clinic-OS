import { defineConfig, devices } from '@playwright/test'

// E2e suite runs every flow in both locales (docs/03 §6): UC specs land per
// milestone; M0 ships the login smoke test.
export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  use: {
    baseURL: 'http://localhost:5173',
    trace: 'on-first-retry',
  },
  projects: [
    {
      name: 'chromium-en',
      use: { ...devices['Desktop Chrome'], locale: 'en-US' },
    },
    {
      name: 'chromium-ar',
      use: { ...devices['Desktop Chrome'], locale: 'ar-SA' },
    },
  ],
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:5173',
    reuseExistingServer: !process.env.CI,
  },
})
