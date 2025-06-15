const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ 
    headless: false, 
    slowMo: 300 
  });
  const page = await browser.newPage();

  try {
    console.log('🚀 Direct currency check...\n');
    
    // Login first
    await page.goto('http://localhost:5001/');
    await page.waitForTimeout(1000);
    
    try {
      await page.click('text=Login', { timeout: 2000 });
      await page.waitForTimeout(500);
    } catch (e) {
      console.log('Already on login screen');
    }
    
    await page.fill('input[type="text"], input[type="email"]', 'ben.weeks');
    await page.fill('input[type="password"]', 'zUYmy&05&uZ$3kmf*^T8');
    await page.click('button:has-text("LOGIN")');
    
    await page.waitForSelector('text=Lightning', { timeout: 10000 });
    console.log('✅ Logged in\n');
    
    // Go directly to allowance page
    await page.goto('http://localhost:5001/allowance');
    await page.waitForTimeout(2000);
    console.log('✅ On Allowance page\n');
    
    // First check the API
    console.log('📝 Checking API...');
    const apiData = await page.evaluate(async () => {
      try {
        const response = await fetch('/allowance/api/v1/currencies');
        const data = await response.json();
        return { status: response.status, data };
      } catch (error) {
        return { error: error.message };
      }
    });
    
    if (apiData.error) {
      console.log('❌ API Error:', apiData.error);
    } else if (apiData.data) {
      console.log('🔍 API Response:', JSON.stringify(apiData, null, 2));
      if (Array.isArray(apiData.data)) {
        console.log(`📊 API returned ${apiData.data.length} currencies`);
        console.log('First 10:', apiData.data.slice(0, 10));
      } else {
        console.log('⚠️  API returned non-array:', typeof apiData.data);
      }
      console.log('\n');
    } else {
      console.log('❌ Unexpected API response:', apiData);
    }
    
    // Now check the dropdown
    await page.click('button:has-text("New Allowance")');
    await page.waitForSelector('.q-dialog', { timeout: 5000 });
    console.log('✅ Create dialog opened\n');
    
    // Click currency dropdown
    await page.click('.q-select:has-text("Currency")');
    await page.waitForTimeout(1000);
    
    // Count dropdown options
    const dropdownCount = await page.evaluate(() => {
      return document.querySelectorAll('.q-menu .q-item').length;
    });
    
    console.log(`🔍 Dropdown shows ${dropdownCount} options\n`);
    
    // Get first few options
    const firstOptions = await page.evaluate(() => {
      const items = Array.from(document.querySelectorAll('.q-menu .q-item'));
      return items.slice(0, 10).map(item => item.textContent.trim());
    });
    
    console.log('First 10 in dropdown:', firstOptions);
    
    // Take screenshot
    await page.screenshot({ path: 'tests/test-results/currency-dropdown.png' });
    console.log('\n📸 Screenshot saved');
    
    // Compare counts
    if (apiData.data && Array.isArray(apiData.data)) {
      const apiCount = apiData.data.length;
      const expectedDropdown = apiCount + 1; // +1 for 'sats'
      
      if (dropdownCount === expectedDropdown) {
        console.log(`\n✅ Counts match! API: ${apiCount}, Dropdown: ${dropdownCount} (includes 'sats')`);
      } else {
        console.log(`\n⚠️  Count mismatch! API: ${apiCount}, Dropdown: ${dropdownCount}`);
        console.log(`Expected ${expectedDropdown} in dropdown (API + 'sats')`);
      }
    }
    
  } catch (error) {
    console.error('\n❌ Error:', error.message);
    await page.screenshot({ path: 'tests/test-results/currency-error.png' });
  } finally {
    await page.waitForTimeout(3000); // Let user see
    await browser.close();
    console.log('\n✅ Done');
  }
})();