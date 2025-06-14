const { chromium } = require('playwright');

// Helper function to login
async function loginAsAdmin(page) {
  await page.goto('http://localhost:5001/');
  
  // Wait for page to load
  await page.waitForTimeout(1000);
  
  // Check if we're on Create Account screen
  const createAccountVisible = await page.isVisible('text=Create Account');
  if (createAccountVisible) {
    console.log('📝 Found Create Account screen, switching to Login...');
    await page.click('text=Login');
    await page.waitForTimeout(1000);
  }
  
  // Fill login form
  console.log('🔑 Filling login credentials...');
  const usernameInput = await page.waitForSelector('[aria-label="Username or Email *"]', { timeout: 10000 });
  await usernameInput.fill('admin');
  
  const passwordInput = await page.waitForSelector('[aria-label="Password *"]', { timeout: 10000 });
  await passwordInput.fill('admin');
  
  // Click login button
  await page.getByRole('button', { name: 'Login' }).click();
  
  // Wait for successful login
  await page.waitForSelector('text=Add a new wallet', { timeout: 15000 });
  console.log('✅ Login successful');
}

(async () => {
  const browser = await chromium.launch({ 
    headless: false, 
    slowMo: 500 
  });
  const page = await browser.newPage();

  try {
    console.log('🚀 Starting currency check test...');
    
    // Login
    console.log('📝 Step 1: Logging in as admin...');
    await loginAsAdmin(page);

    // Navigate to allowance
    console.log('📝 Step 2: Navigating to allowance extension...');
    await page.click('.q-drawer__backdrop', { force: true }).catch(() => {});
    await page.locator('.q-item').filter({ hasText: 'Allowance' }).click();
    await page.waitForURL('**/allowance', { timeout: 10000 });
    console.log('✅ Navigated to allowance extension');

    // Open create dialog
    console.log('📝 Step 3: Opening create allowance dialog...');
    await page.click('button:has-text("New Allowance")');
    await page.waitForSelector('.q-dialog', { timeout: 5000 });
    console.log('✅ Create dialog opened');

    // Click on currency dropdown
    console.log('📝 Step 4: Checking currency dropdown...');
    await page.click('.q-select:has-text("Currency")');
    await page.waitForTimeout(1000); // Wait for dropdown to open

    // Get all currency options
    const currencyOptions = await page.evaluate(() => {
      const options = Array.from(document.querySelectorAll('.q-menu .q-item'));
      return options.map(opt => opt.textContent.trim());
    });

    console.log('🔍 Available currencies:', currencyOptions);
    console.log(`📊 Total currencies found: ${currencyOptions.length}`);

    // Also check the API directly
    console.log('\n📝 Step 5: Checking API endpoint...');
    const apiResponse = await page.evaluate(async () => {
      try {
        const response = await fetch('/allowance/api/v1/currencies');
        const data = await response.json();
        return { status: response.status, data };
      } catch (error) {
        return { error: error.message };
      }
    });
    
    console.log('🔍 API Response:', apiResponse);

    // Take screenshot
    await page.screenshot({ path: 'tests/test-results/currency-dropdown.png' });
    console.log('📸 Screenshot saved to currency-dropdown.png');

  } catch (error) {
    console.error('❌ Error:', error);
    await page.screenshot({ path: 'tests/test-results/currency-error.png' });
  } finally {
    await browser.close();
    console.log('\n✅ Test completed');
  }
})();