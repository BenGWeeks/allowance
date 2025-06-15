const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: false, slowMo: 1000 });
  const page = await browser.newPage();

  try {
    console.log('🚀 Starting admin login test...');
    
    // Go to LNBits
    await page.goto('http://localhost:5001/');
    await page.waitForLoadState('networkidle');
    
    // Check if we see the create account screen or login link
    const createAccountVisible = await page.locator('text=Create Account').first().isVisible();
    
    if (createAccountVisible) {
      console.log('📝 Found Create Account screen, switching to Login...');
      // Click on the Login link to switch to login form
      await page.click('text=Login');
      await page.waitForTimeout(2000);
    }
    
    // Fill login form
    console.log('🔑 Filling login credentials...');
    await page.fill('input[type="text"], input[type="email"]', 'ben.weeks');
    await page.fill('input[type="password"]', 'zUYmy&05&uZ$3kmf*^T8');
    
    // Click LOGIN button
    await page.click('button:has-text("LOGIN")');
    await page.waitForTimeout(3000);
    
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