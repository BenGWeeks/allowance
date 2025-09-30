const { chromium } = require('playwright');
const { login, getConfig } = require('../auth-helper');

(async () => {
  const browser = await chromium.launch({ headless: true, slowMo: 1000 });
  const page = await browser.newPage();
  const config = getConfig();

  try {
    console.log('🚀 Starting enable allowance extension test...');
    
    // Listen for console errors
    page.on('console', msg => {
      if (msg.type() === 'error') {
        console.log('❌ Browser console error:', msg.text());
      }
    });
    
    page.on('pageerror', error => {
      console.log('💥 Page error:', error.message);
    });
    
    // Step 1: Login first (reuse login logic)
    console.log('📝 Step 1: Logging in as admin...');
    await login(page);
    console.log('✅ Login successful');
    
    // Close any open dialogs that might be blocking clicks
    const dialogVisible = await page.locator('.q-dialog').isVisible();
    if (dialogVisible) {
      console.log('📝 Closing open dialog...');
      await page.keyboard.press('Escape');
      await page.waitForTimeout(1000);
    }
    
    // Step 2: Navigate to Extensions
    console.log('📝 Step 2: Navigating to Extensions...');
    await page.click('a:has-text("Extensions")');
    await page.waitForTimeout(3000);
    
    // Step 3: Find and enable Allowance extension
    console.log('📝 Step 3: Looking for Allowance extension...');
    
    // Find the card that contains "Allowance" text
    const allowanceCard = page.locator('.q-card:has(.text-h5:has-text("Allowance"))');
    
    if (!(await allowanceCard.isVisible())) {
      console.log('❌ Allowance extension card not found');
      await page.screenshot({ path: 'tests/test-results/enable-allowance-not-found.png', fullPage: true });
      process.exit(1);
    }
    
    console.log('✅ Found Allowance extension card');
    
    // Step 4: Check if extension is already enabled, if not enable it
    console.log('📝 Step 4: Checking extension status...');
    const disableButtonVisible = await allowanceCard.locator('button:has-text("Disable")').isVisible();
    
    if (disableButtonVisible) {
      console.log('✅ Extension is already enabled (Disable button visible)');
    } else {
      console.log('📝 Extension not enabled, looking for Enable button...');
      
      // Look for Enable button or toggle to enable
      const enableButton = allowanceCard.locator('button:has-text("Enable")');
      const toggleButton = allowanceCard.locator('.q-toggle');
      
      if (await enableButton.isVisible()) {
        console.log('📝 Clicking Enable button...');
        await enableButton.click();
      } else if (await toggleButton.isVisible()) {
        console.log('📝 Clicking toggle...');
        await toggleButton.click();
      } else {
        console.log('❌ No Enable button or toggle found');
        await page.screenshot({ path: 'tests/test-results/enable-allowance-no-enable-button.png', fullPage: true });
        process.exit(1);
      }
      
      await page.waitForTimeout(2000);
      
      // Re-check if enabled by looking for Disable button
      const newDisableButtonVisible = await allowanceCard.locator('button:has-text("Disable")').isVisible();
      
      if (!newDisableButtonVisible) {
        console.log('❌ Failed to enable extension - Disable button not found');
        await page.screenshot({ path: 'tests/test-results/enable-allowance-enable-failed.png', fullPage: true });
        process.exit(1);
      }
      
      console.log('✅ Extension enabled successfully (Disable button now visible)');
    }
    
    const enabledIndicator = await allowanceCard.locator('button:has-text("Disable")').isVisible();
    
    if (enabledIndicator) {
      console.log('✅ Allowance extension enabled successfully!');
      await page.screenshot({ path: 'tests/test-results/enable-allowance-success.png', fullPage: true });
      
      // Try to navigate to the allowance extension to verify it works
      console.log('📝 Step 5: Verifying extension access...');
      
      // Check cookies before navigation
      const cookies = await page.context().cookies();
      console.log('🍪 Number of cookies:', cookies.length);
      
      // Track all responses during navigation
      page.on('response', response => {
        console.log(`📡 Response: ${response.status()} ${response.url()}`);
      });
      
      const response = await page.goto(`${config.baseUrl}/allowance/`);
      console.log('📡 Final Response status:', response.status());
      console.log('📡 Final Response URL:', response.url());
      
      // Check for any redirects
      const finalUrl = page.url();
      if (finalUrl !== `${config.baseUrl}/allowance/`) {
        console.log('🔄 Page was redirected to:', finalUrl);
      }
      
      // Check if we got redirected to login
      if (response.url().includes('first_install') || response.url().includes('login')) {
        console.log('🔄 Got redirected to login - session lost');
      }
      
      // Wait for page to load and capture any errors
      await page.waitForTimeout(3000);
      console.log('📝 Waiting for Vue app to initialize...');
      await page.waitForTimeout(2000);
      
      const allowancePageLoaded = await page.locator('text="New Allowance"').isVisible();
      if (allowancePageLoaded) {
        console.log('✅ Allowance extension is accessible!');
        await page.screenshot({ path: 'tests/test-results/enable-allowance-verified.png', fullPage: true });
        process.exit(0); // Success
      } else {
        console.log('⚠️ Extension enabled but page not accessible');
        console.log('📝 Checking for Vue app elements...');
        
        // Check what's actually on the page
        const pageTitle = await page.title();
        console.log('📄 Page title:', pageTitle);
        
        const vueElement = await page.locator('#vue').isVisible();
        console.log('🔍 Vue element present:', vueElement);
        
        const bodyText = await page.locator('body').textContent();
        if (bodyText.includes('ALLOWANCE EXTENSION TEST - BASIC TEMPLATE')) {
          console.log('✓ Basic template is rendering!');
        } else {
          console.log('✗ Basic template not rendering');
        }
        
        if (bodyText.includes('Missing user ID or access token')) {
          console.log('🔑 Authentication issue - session lost');
        } else if (bodyText.includes('first_install')) {
          console.log('🔄 Redirected to setup page');  
        } else if (bodyText.includes('WINDOW_SETTINGS')) {
          console.log('🏠 Getting LNBits homepage instead of extension');
        }
        
        console.log('📝 Page content preview:', bodyText.substring(0, 300));
        
        await page.screenshot({ path: 'tests/test-results/enable-allowance-debug.png', fullPage: true });
        process.exit(1); // Failure
      }
    } else {
      console.log('❌ Failed to enable Allowance extension');
      await page.screenshot({ path: 'tests/test-results/enable-allowance-failed.png', fullPage: true });
      process.exit(1); // Failure
    }
    
  } catch (error) {
    console.error('💥 Error:', error.message);
    await page.screenshot({ path: 'tests/test-results/enable-allowance-error.png', fullPage: true });
    process.exit(1); // Failure
  } finally {
    await browser.close();
  }
})();