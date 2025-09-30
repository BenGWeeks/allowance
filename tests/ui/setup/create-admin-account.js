const { chromium } = require('playwright');
const { login, getConfig } = require('../auth-helper');

(async () => {
  const browser = await chromium.launch({ headless: true, slowMo: 1000 });
  const page = await browser.newPage();
  const config = getConfig();

  try {
    console.log('🚀 Starting admin account creation...');

    // Go to LNBits
    await page.goto(config.baseUrl);
    await page.waitForLoadState('networkidle');
    
    // Check if we see the superuser setup screen or if already logged in
    const superuserSetupVisible = await page.locator('text="Set up the Superuser account below."').isVisible();
    const createAccountVisible = await page.locator('text="Create account"').first().isVisible();
    const walletDashboardVisible = await page.locator('text="Add a new wallet"').isVisible();
    const loginVisible = await page.locator('text="Login"').first().isVisible();
    
    // If wallet dashboard is visible, admin is already logged in
    if (walletDashboardVisible) {
      console.log('✅ Admin account appears to be already logged in - test passed');
      await browser.close();
      process.exit(0);
    }
    
    // If login screen is visible, admin account already exists
    if (loginVisible && !superuserSetupVisible) {
      console.log('✅ Login screen visible - admin account already exists - test passed');
      await browser.close();
      process.exit(0);
    }
    
    if (!superuserSetupVisible && !createAccountVisible) {
      console.log('⚠️ Neither superuser setup nor create account screen visible. Admin account may already exist.');
      console.log('✅ Admin account appears to already be set up - test passed');
      await browser.close();
      process.exit(0); // Exit successfully - not an error if account exists
    }
    
    console.log('📝 Found Superuser setup screen, creating admin account...');
    
    // Try multiple selectors for form fields
    const usernameSelectors = [
      '[aria-label="Username"]',
      'input[type="text"]',
      'input[placeholder*="username" i]',
      'input[placeholder*="user" i]',
      '.q-field:has-text("Username") input'
    ];
    
    const passwordSelectors = [
      '[aria-label="Password"]',
      'input[type="password"]',
      'input[placeholder*="password" i]',
      '.q-field:has-text("Password") input[type="password"]'
    ];
    
    // Fill username
    let filled = false;
    for (const selector of usernameSelectors) {
      try {
        await page.fill(selector, config.username, { timeout: 5000 });
        console.log(`✅ Filled username using selector: ${selector}`);
        filled = true;
        break;
      } catch (e) {
        // Try next selector
      }
    }
    
    if (!filled) {
      console.log('❌ Could not find username field');
      await page.screenshot({ path: 'tests/test-results/create-account-error.png', fullPage: true });
      process.exit(1);
    }
    
    // Fill passwords
    const passwordFields = await page.locator('input[type="password"]').all();
    if (passwordFields.length >= 2) {
      await passwordFields[0].fill(config.password);
      console.log('✅ Filled password field');
      await passwordFields[1].fill(config.password);
      console.log('✅ Filled password confirmation field');
    } else {
      console.log('❌ Could not find password fields');
      await page.screenshot({ path: 'tests/test-results/create-account-error.png', fullPage: true });
      process.exit(1);
    }
    
    // Take screenshot before submitting
    await page.screenshot({ path: 'tests/test-results/create-account-form.png', fullPage: true });
    console.log('📸 Form screenshot saved');
    
    // Submit the form - look for submit button
    console.log('🖱️ Looking for submit button...');
    
    const submitSelectors = [
      'button:has-text("Login")',
      'button:has-text("Create")',
      'button:has-text("Submit")',
      'button[type="submit"]'
    ];
    
    let submitted = false;
    for (const selector of submitSelectors) {
      try {
        const button = page.locator(selector).first();
        if (await button.isVisible({ timeout: 3000 })) {
          await button.click();
          console.log(`✅ Clicked submit button: ${selector}`);
          submitted = true;
          break;
        }
      } catch (e) {
        // Try next selector
      }
    }
    
    if (!submitted) {
      console.log('❌ Could not find submit button');
      await page.screenshot({ path: 'tests/test-results/create-account-error.png', fullPage: true });
      process.exit(1);
    }
    
    // Wait for navigation to complete
    console.log('⏳ Waiting for account creation to complete...');
    await page.waitForTimeout(5000);
    
    // Check if we're now on the wallet page
    const isSuccess = await page.locator('text="Add a new wallet"').isVisible();
    
    if (isSuccess) {
      console.log('✅ Successfully created admin account!');
      await page.screenshot({ path: 'tests/test-results/create-account-success.png', fullPage: true });
      await browser.close();
      process.exit(0); // Success
    } else {
      console.log('❌ Admin account creation might have failed');
      await page.screenshot({ path: 'tests/test-results/create-account-error.png', fullPage: true });
      await browser.close();
      process.exit(1); // Failure
    }
    
  } catch (error) {
    console.error('💥 Error:', error.message);
    await page.screenshot({ path: 'tests/test-results/create-account-error.png', fullPage: true });
    await browser.close();
    process.exit(1); // Failure
  }
})();