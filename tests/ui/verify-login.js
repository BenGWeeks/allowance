const { chromium } = require('playwright');
const { login, getConfig } = require('./auth-helper');

(async () => {
  const browser = await chromium.launch({ headless: false, slowMo: 1000 });
  const page = await browser.newPage();
  const config = getConfig();

  try {
    console.log('🚀 Starting admin login test...');

    // Test login using the auth helper
    await login(page);

    // Check if login was successful by looking for "Add a new wallet" text
    const walletVisible = await page.locator('text="Add a new wallet"').isVisible();

    if (walletVisible) {
      console.log('✅ Login successful! Wallet dashboard visible.');
      await page.screenshot({ path: 'tests/test-results/login-success.png', fullPage: true });
      console.log('📸 Screenshot saved to test-results/login-success.png');
      process.exit(0); // Success
    } else {
      console.log('❌ Login failed - wallet not visible');
      await page.screenshot({ path: 'tests/test-results/login-failed.png', fullPage: true });
      process.exit(1); // Failure
    }
    
  } catch (error) {
    console.error('💥 Error during login:', error.message);
    await page.screenshot({ path: 'tests/test-results/login-error.png', fullPage: true });
    process.exit(1); // Failure
  } finally {
    await browser.close();
  }
})();