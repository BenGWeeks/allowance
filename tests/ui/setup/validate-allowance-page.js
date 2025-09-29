#!/usr/bin/env node

// Load environment variables from .env.local
const { chromium } = require('playwright');
const { getConfig, login } = require('./auth-helper');

(async () => {
  const { baseUrl } = getConfig();

  // Launch browser
  const browser = await chromium.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });

  try {
    const context = await browser.newContext();
    const page = await context.newPage();

    // Navigate to LNBits
    console.log('📍 Navigating to:', baseUrl);
    await page.goto(baseUrl);

    // Login
    console.log('🔑 Logging in...');
    await login(page);

    // Navigate to the allowance extension
    console.log('🚀 Navigating to allowance extension...');
    await page.goto(`${baseUrl}/allowance/`);

    // Wait for the page to load
    await page.waitForLoadState('networkidle');

    // Check for our test message
    const testHeader = await page.$('h1:has-text("Test - Allowance Extension")');
    if (testHeader) {
      console.log('✅ Test HTML is showing - route is working!');
      process.exit(0);
    }

    // Check for error messages
    const errorElement = await page.$('.q-notification__message:has-text("error")');
    const serverErrorElement = await page.$('text=/500 INTERNAL SERVER ERROR/i');
    const walletTypeErrorElement = await page.$('text=/WalletTypeInfo.*has no attribute/i');

    if (errorElement) {
      const errorText = await errorElement.textContent();
      console.error('❌ Error notification found:', errorText);
      process.exit(1);
    }

    if (serverErrorElement) {
      console.error('❌ 500 Internal Server Error found on page');
      process.exit(1);
    }

    if (walletTypeErrorElement) {
      console.error('❌ WalletTypeInfo error found on page');
      process.exit(1);
    }

    // Check that the allowance page loaded successfully
    const pageTitle = await page.textContent('h5:has-text("Allowances"), .text-h5:has-text("Allowance")');
    if (!pageTitle) {
      // Check if we at least have the New Allowance button
      const newAllowanceBtn = await page.$('[data-cy="new-allowance-btn"], button:has-text("New Allowance")');
      if (!newAllowanceBtn) {
        console.error('❌ Allowance page did not load correctly - no title or New Allowance button found');

        // Take a screenshot for debugging
        await page.screenshot({ path: 'tests/test-results/view-allowances-error.png' });
        console.log('📸 Screenshot saved to tests/test-results/view-allowances-error.png');

        process.exit(1);
      }
    }

    // Take a success screenshot
    await page.screenshot({ path: 'tests/test-results/view-allowances-success.png' });

    console.log('✅ SUCCESS: Allowance page loaded without errors');

  } catch (error) {
    console.error('❌ Test failed:', error.message);
    process.exit(1);
  } finally {
    await browser.close();
  }
})();