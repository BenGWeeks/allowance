// @ts-check
const {defineConfig, devices} = require('@playwright/test');
const {getConfig} = require('./ui/auth-helper');

module.exports = defineConfig({
  testDir: './ui',
  testMatch: '**/*.spec.js',
  timeout: 90000,
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: 0,
  workers: 1,
  reporter: [['html', {open: 'never'}]],
  use: {
    baseURL: getConfig().baseUrl,
    locale: 'en-GB',
    // Traces can expose credentials and API keys.
    trace: 'off',
    actionTimeout: 15000,
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    viewport: {width: 1280, height: 720}
  },
  projects: [{name: 'chromium', use: {...devices['Desktop Chrome']}}]
});
