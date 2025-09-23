#!/usr/bin/env node

const { chromium } = require('playwright');
const { getConfig } = require('./auth-helper');

async function simpleLoginTest() {
  const browser = await chromium.launch({
    headless: false,
    slowMo: 100
  });
  const context = await browser.newContext();
  const page = await context.newPage();
  const config = getConfig();

  try {
    console.log('Testing login with credentials...');
    console.log('URL:', config.baseUrl);
    console.log('Username:', config.username);
    console.log('Password:', config.password);

    // Navigate to login page
    await page.goto(`${config.baseUrl}/login`);
    await page.waitForLoadState('networkidle');

    // Screenshot before login
    await page.screenshot({ path: 'simple-login-1-before.png', fullPage: true });
    console.log('Screenshot saved: simple-login-1-before.png');

    // Fill in credentials
    const usernameInput = page.locator('input[type="text"], input[placeholder*="sername"], input[aria-label*="sername"]').first();
    const passwordInput = page.locator('input[type="password"], input[placeholder*="assword"], input[aria-label*="assword"]').first();

    await usernameInput.fill(config.username);
    await passwordInput.fill(config.password);

    // Screenshot after filling
    await page.screenshot({ path: 'simple-login-2-filled.png', fullPage: true });
    console.log('Screenshot saved: simple-login-2-filled.png');

    // Click login button
    const loginButton = page.locator('button:has-text("Login"), button:has-text("Sign in"), button[type="submit"]').first();
    await loginButton.click();

    // Wait for navigation
    await page.waitForLoadState('networkidle', { timeout: 10000 });

    // Screenshot after login attempt
    await page.screenshot({ path: 'simple-login-3-after.png', fullPage: true });
    console.log('Screenshot saved: simple-login-3-after.png');

    // Check if login successful
    const currentUrl = page.url();
    console.log('Current URL:', currentUrl);

    if (currentUrl.includes('/wallet') || currentUrl.includes('/admin')) {
      console.log('✅ Login successful!');
    } else {
      console.log('❌ Login failed - still on:', currentUrl);

      // Check for error messages
      const errorMessages = await page.locator('.q-notification, .error, [role="alert"]').allTextContents();
      if (errorMessages.length > 0) {
        console.log('Error messages:', errorMessages);
      }
    }

    await browser.close();
    return 0;

  } catch (error) {
    console.error('❌ Error during test:', error.message);
    await page.screenshot({ path: 'simple-login-error.png', fullPage: true });
    await browser.close();
    return 1;
  }
}

// Run the test
simpleLoginTest().then(exitCode => {
  process.exit(exitCode);
});