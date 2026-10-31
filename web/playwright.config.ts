import { defineConfig, devices } from '@playwright/test';

// Runs against the built app served by the API: `make build`, then the API on :8000
// with E2E_PASSWORD set to the password whose hash is in .env.
export default defineConfig({
  testDir: 'e2e',
  use: { baseURL: process.env.E2E_BASE_URL || 'http://localhost:8000', launchOptions: process.env.PW_CHROMIUM ? { executablePath: process.env.PW_CHROMIUM } : {} },
  projects: [
    { name: 'desktop', use: { viewport: { width: 1280, height: 800 } } },
    { name: 'phone', use: { ...devices['iPhone 13'].viewport && { viewport: { width: 375, height: 812 }, isMobile: true, hasTouch: true } } },
  ],
});
