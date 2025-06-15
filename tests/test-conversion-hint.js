const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ 
    headless: false, 
    slowMo: 500 
  });
  const page = await browser.newPage();

  try {
    console.log('🚀 Testing conversion hint...\n');
    
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
    
    // Fill in amount
    await page.fill('input[type="number"]', '100');
    console.log('✅ Filled amount: 100\n');
    
    // Select USD currency
    await page.click('.q-select:has-text("Currency")');
    await page.waitForTimeout(500);
    await page.click('.q-item:has-text("USD")');
    console.log('✅ Selected USD currency\n');
    
    // Wait for conversion to appear
    await page.waitForTimeout(2000);
    
    // Check for hint text
    const hintText = await page.evaluate(() => {
      const hints = Array.from(document.querySelectorAll('.q-field__bottom'));
      return hints.map(h => h.textContent.trim()).filter(t => t.includes('sats'));
    });
    
    console.log('🔍 Hint texts found:', hintText);
    
    // Check console for rate message
    const consoleLogs = await page.evaluate(() => {
      return window.consoleLogs || [];
    });
    
    // Take screenshot
    await page.screenshot({ path: 'tests/test-results/conversion-hint-usd.png' });
    console.log('📸 Screenshot saved\n');
    
    // Try EUR
    await page.click('.q-select:has-text("USD")');
    await page.waitForTimeout(500);
    await page.click('.q-item:has-text("EUR")');
    await page.waitForTimeout(2000);
    
    const hintTextEur = await page.evaluate(() => {
      const hints = Array.from(document.querySelectorAll('.q-field__bottom'));
      return hints.map(h => h.textContent.trim()).filter(t => t.includes('sats'));
    });
    
    console.log('🔍 EUR hint texts:', hintTextEur);
    
    await page.screenshot({ path: 'tests/test-results/conversion-hint-eur.png' });
    
    // Check the actual input hint
    const amountFieldHint = await page.evaluate(() => {
      const amountInput = document.querySelector('input[type="number"]');
      if (amountInput) {
        const field = amountInput.closest('.q-field');
        const hint = field?.querySelector('.q-field__bottom');
        return hint?.textContent || 'No hint found';
      }
      return 'Amount input not found';
    });
    
    console.log('📝 Amount field hint:', amountFieldHint);
    
  } catch (error) {
    console.error('\n❌ Error:', error.message);
    await page.screenshot({ path: 'tests/test-results/conversion-error.png' });
  } finally {
    await browser.close();
    console.log('\n✅ Done');
  }
})();