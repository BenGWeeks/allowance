const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ 
    headless: false, 
    slowMo: 300 
  });
  const page = await browser.newPage();

  try {
    console.log('🚀 Quick currency check...\n');
    
    // Use the existing login test approach
    await page.goto('http://localhost:5001/');
    await page.waitForTimeout(1000);
    
    // Try to click Login if visible
    try {
      await page.click('text=Login', { timeout: 2000 });
      await page.waitForTimeout(500);
    } catch (e) {
      console.log('Already on login screen');
    }
    
    // Fill credentials using the working method from login test
    await page.fill('input[type="text"], input[type="email"]', 'ben.weeks');
    await page.fill('input[type="password"]', 'zUYmy&05&uZ$3kmf*^T8');
    await page.getByRole('button', { name: 'Login' }).click();
    
    // Wait for wallet screen
    await page.waitForSelector('text=Lightning', { timeout: 10000 });
    console.log('✅ Logged in successfully\n');
    
    // Navigate to allowance
    await page.waitForTimeout(1000);
    
    // Close any dialogs that might be open
    try {
      await page.click('.q-dialog__backdrop', { timeout: 1000 });
      await page.waitForTimeout(500);
    } catch (e) {
      // No dialog to close
    }
    
    // Navigate to allowance
    await page.locator('.q-item').filter({ hasText: 'Allowance' }).first().click();
    await page.waitForURL('**/allowance', { timeout: 10000 });
    console.log('✅ In Allowance extension\n');
    
    // Open create dialog
    await page.click('button:has-text("New Allowance")');
    await page.waitForSelector('.q-dialog', { timeout: 5000 });
    console.log('✅ Create dialog opened\n');
    
    // Check currencies via API
    console.log('📝 Checking API endpoint...');
    const apiCurrencies = await page.evaluate(async () => {
      try {
        const response = await fetch('/allowance/api/v1/currencies');
        return await response.json();
      } catch (error) {
        return { error: error.message };
      }
    });
    
    console.log('🔍 API Currencies:', apiCurrencies);
    console.log(`📊 Total from API: ${Array.isArray(apiCurrencies) ? apiCurrencies.length : 0}\n`);
    
    // Click currency dropdown
    console.log('📝 Checking dropdown...');
    await page.click('.q-select:has-text("Currency")');
    await page.waitForTimeout(1000);
    
    // Get dropdown options
    const dropdownCurrencies = await page.evaluate(() => {
      const items = document.querySelectorAll('.q-menu .q-item');
      return Array.from(items).map(item => item.textContent.trim());
    });
    
    console.log('🔍 Dropdown Currencies:', dropdownCurrencies);
    console.log(`📊 Total in dropdown: ${dropdownCurrencies.length}\n`);
    
    // Compare
    if (Array.isArray(apiCurrencies) && dropdownCurrencies.length > 0) {
      const missingInDropdown = apiCurrencies.filter(c => !dropdownCurrencies.includes(c));
      const extraInDropdown = dropdownCurrencies.filter(c => !apiCurrencies.includes(c) && c !== 'sats');
      
      if (missingInDropdown.length > 0) {
        console.log('⚠️  Missing in dropdown:', missingInDropdown);
      }
      if (extraInDropdown.length > 0) {
        console.log('⚠️  Extra in dropdown:', extraInDropdown);
      }
      if (missingInDropdown.length === 0 && extraInDropdown.length === 0) {
        console.log('✅ Dropdown matches API (plus "sats")');
      }
    }
    
    // Take screenshot
    await page.screenshot({ path: 'tests/test-results/currency-dropdown-open.png' });
    console.log('\n📸 Screenshot saved');
    
  } catch (error) {
    console.error('\n❌ Error:', error.message);
    await page.screenshot({ path: 'tests/test-results/currency-check-error.png' });
  } finally {
    await page.waitForTimeout(2000); // Let user see the result
    await browser.close();
    console.log('\n✅ Test completed');
  }
})();