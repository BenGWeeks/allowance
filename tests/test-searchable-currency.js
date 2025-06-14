const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ 
    headless: false, 
    slowMo: 300 
  });
  const page = await browser.newPage();

  try {
    console.log('🚀 Testing searchable currency dropdown...\n');
    
    // Login
    await page.goto('http://localhost:5001/');
    await page.waitForTimeout(1000);
    
    try {
      await page.click('text=Login', { timeout: 2000 });
      await page.waitForTimeout(500);
    } catch (e) {}
    
    await page.fill('input[type="text"], input[type="email"]', 'ben.weeks');
    await page.fill('input[type="password"]', 'zUYmy&05&uZ$3kmf*^T8');
    await page.click('button:has-text("LOGIN")');
    
    await page.waitForSelector('text=Lightning', { timeout: 10000 });
    console.log('✅ Logged in\n');
    
    // Go to allowance
    await page.goto('http://localhost:5001/allowance');
    await page.waitForTimeout(2000);
    
    // Open create dialog
    await page.click('button:has-text("New Allowance")');
    await page.waitForSelector('.q-dialog', { timeout: 5000 });
    console.log('✅ Create dialog opened\n');
    
    // Click currency dropdown
    console.log('📝 Testing currency search...');
    await page.click('.q-select:has-text("Currency")');
    await page.waitForTimeout(500);
    
    // Type to search
    await page.keyboard.type('USD');
    await page.waitForTimeout(1000);
    
    // Count filtered results
    const filteredCount = await page.evaluate(() => {
      return document.querySelectorAll('.q-menu .q-item').length;
    });
    
    console.log(`🔍 Searching for "USD" shows ${filteredCount} results`);
    
    // Clear and search for something else
    await page.keyboard.press('Control+A');
    await page.keyboard.type('EUR');
    await page.waitForTimeout(1000);
    
    const eurCount = await page.evaluate(() => {
      return document.querySelectorAll('.q-menu .q-item').length;
    });
    
    console.log(`🔍 Searching for "EUR" shows ${eurCount} results`);
    
    // Clear and check all
    await page.keyboard.press('Control+A');
    await page.keyboard.press('Delete');
    await page.waitForTimeout(1000);
    
    const allCount = await page.evaluate(() => {
      return document.querySelectorAll('.q-menu .q-item').length;
    });
    
    console.log(`🔍 Showing all currencies: ${allCount} options`);
    
    // Take screenshot
    await page.screenshot({ path: 'tests/test-results/searchable-currency.png' });
    console.log('\n📸 Screenshot saved');
    
  } catch (error) {
    console.error('\n❌ Error:', error.message);
    await page.screenshot({ path: 'tests/test-results/currency-search-error.png' });
  } finally {
    await page.waitForTimeout(2000);
    await browser.close();
    console.log('\n✅ Done');
  }
})();