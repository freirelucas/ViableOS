import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright configuration for ViableOS Frontend
 * Automatically starts the Vite dev server before tests
 */
export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,

  reporter: [
    ['list'],
    ['html', { open: 'never' }],
  ],

  use: {
    baseURL: 'http://localhost:5173',
    screenshot: 'only-on-failure',
    trace: 'on-first-retry',
    video: 'retain-on-failure',
  },

  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],

  webServer: [
    {
      command: 'npm run dev',
      url: 'http://localhost:5173',
      reuseExistingServer: !process.env.CI,
      timeout: 30_000,
    },
    // Backend (FastAPI on port 8000) - uncomment to start automatically
    // {
    //   command: 'cd ../src && python -m uvicorn viableos.api.main:app --port 8000',
    //   url: 'http://localhost:8000/health',
    //   reuseExistingServer: !process.env.CI,
    //   timeout: 30_000,
    // },
  ],
});
