const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true, slowMo: 1000 });
  const page = await browser.newPage();

  try {
    console.log('🚀 Starting admin account creation...');
    
    // Go to LNBits
    await page.goto('http://localhost:5001/');
    await page.waitForLoadState('networkidle');
    
    // Check if we see the superuser setup screen
    const superuserSetupVisible = await page.locator('text="Set up the Superuser account below."').isVisible() || await page.locator('text="Create account"').first().isVisible();
    
    if (!superuserSetupVisible) {
      console.log('⚠️ Superuser setup screen not visible. Admin account may already exist.');
      console.log('✅ Admin account appears to already be set up - test passed');
      await browser.close();
      process.exit(0); // Exit successfully - not an error if account exists
    }
    
    console.log('📝 Found Superuser setup screen, creating admin account...');
    
    // Fill in the superuser account form using aria-label selectors
    // Username
    await page.fill('[aria-label="Username"]', 'ben.weeks');
    
    // Password
    await page.fill('[aria-label="Password"]', 'zUYmy&05&uZ$3kmf*^T8');
    
    // Confirm password
    await page.fill('[aria-label="Password repeat"]', 'zUYmy&05&uZ$3kmf*^T8');
    
    // Take screenshot before submitting
    await page.screenshot({ path: 'tests/test-results/create-account-form.png', fullPage: true });
    console.log('📸 Form screenshot saved');
    
    // Submit the form - wait for button to be enabled
    console.log('🖱️ Waiting for Login button to be enabled...');
    await page.waitForSelector('button:has-text("Login"):not([disabled])', { timeout: 5000 });
    
    console.log('🖱️ Creating superuser account...');
    await page.click('button:has-text("Login")');
    await page.waitForTimeout(5000);
    
    // Check if account was created successfully
    const addWalletVisible = await page.locator('text="Add a new wallet"').isVisible();
    const errorVisible = await page.locator('.q-notification--negative, .error').isVisible() || await page.locator('text=error').isVisible();
    
    if (addWalletVisible) {
      console.log('✅ Admin account created successfully!');
      console.log('📝 Username: ben.weeks');
      console.log('🔑 Password: [saved in script]');
      
      // Take final screenshot
      await page.screenshot({ path: 'tests/test-results/create-account-success.png', fullPage: true });
      process.exit(0); // Success
    } else if (errorVisible) {
      console.log('❌ Error creating account. Check screenshot for details.');
      await page.screenshot({ path: 'tests/test-results/create-account-error.png', fullPage: true });
      process.exit(1); // Failure
    } else {
      console.log('⚠️ Unknown state after account creation');
      await page.screenshot({ path: 'tests/test-results/create-account-unknown.png', fullPage: true });
      process.exit(1); // Failure
    }
    
  } catch (error) {
    console.error('💥 Error:', error.message);
    await page.screenshot({ path: 'tests/test-results/create-account-error.png', fullPage: true });
    process.exit(1); // Failure
  } finally {
    await browser.close();
  }
})();