// @ts-check
const { defineConfig, devices } = require('@playwright/test');
const { getConfig } = require('./ui/auth-helper');

// Get configuration from environment variables
const config = getConfig();

/**
 * @see https://playwright.dev/docs/test-configuration
 */
module.exports = defineConfig({
  testDir: './ui/crud',
  testMatch: '**/*.spec.js',
  timeout: 90000,
  /* Run tests in files in parallel */
  fullyParallel: false,
  /* Fail the build on CI if you accidentally left test.only in the source code. */
  forbidOnly: !!process.env.CI,
  /* Do not retry mutations automatically. */
  retries: 0,
  /* Opt out of parallel tests on CI. */
  workers: process.env.CI ? 1 : undefined,
  /* Reporter to use. See https://playwright.dev/docs/test-reporters */
  reporter: 'html',
  /* Shared settings for all the projects below. See https://playwright.dev/docs/api/class-testoptions. */
  use: {
    /* Base URL to use in actions like `await page.goto('/')`. */
    baseURL: config.baseUrl,

    /* Traces may contain credentials and API keys; keep them disabled. */
    trace: 'off',
    actionTimeout: 15000,
    
    /* Take screenshot on failure */
    screenshot: 'only-on-failure',
    
    /* Record video on failure */
    video: 'retain-on-failure',

    /* Viewport size */
    viewport: { width: 1280, height: 720 },
  },

  /* Configure projects for major browsers */
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },

    // {
    //   name: 'firefox',
    //   use: { ...devices['Desktop Firefox'] },
    // },

    // {
    //   name: 'webkit',
    //   use: { ...devices['Desktop Safari'] },
    // },
  ],

});