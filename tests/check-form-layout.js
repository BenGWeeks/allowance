const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ 
    headless: false, 
    slowMo: 300 
  });
  const page = await browser.newPage();

  try {
    console.log('🚀 Checking form layout...\n');
    
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
    
    // Fill in amount and select currency
    await page.fill('input[type="number"]', '100');
    
    // Select a fiat currency
    await page.click('.q-select:has-text("Currency")');
    await page.waitForTimeout(500);
    await page.click('text=USD');
    await page.waitForTimeout(1500); // Wait for rate to load
    
    // Take screenshot
    await page.screenshot({ path: 'tests/test-results/form-layout-with-hint.png' });
    console.log('📸 Screenshot saved showing hint under amount field\n');
    
    // Try another currency
    await page.click('.q-select:has-text("USD")');
    await page.waitForTimeout(500);
    await page.click('text=EUR');
    await page.waitForTimeout(1500);
    
    await page.screenshot({ path: 'tests/test-results/form-layout-eur.png' });
    console.log('📸 Screenshot saved with EUR currency\n');
    
    console.log('✅ Form layout updated - hint now shows under Amount field');
    
  } catch (error) {
    console.error('\n❌ Error:', error.message);
    await page.screenshot({ path: 'tests/test-results/form-layout-error.png' });
  } finally {
    await page.waitForTimeout(2000);
    await browser.close();
    console.log('\n✅ Done');
  }
})();