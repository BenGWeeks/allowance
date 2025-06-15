const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ 
    headless: false, 
    slowMo: 500 
  });
  const page = await browser.newPage();

  try {
    console.log('🚀 Starting currency debug...');
    
    // Go to homepage
    await page.goto('http://localhost:5001/');
    await page.waitForTimeout(2000);
    
    // Take screenshot of current state
    await page.screenshot({ path: 'tests/test-results/currency-login-state.png' });
    console.log('📸 Screenshot saved of login state');
    
    // Try different selectors
    console.log('🔍 Looking for login elements...');
    
    const loginLink = await page.$('text=Login');
    console.log('Login link found:', !!loginLink);
    
    if (loginLink) {
      await loginLink.click();
      await page.waitForTimeout(1000);
      await page.screenshot({ path: 'tests/test-results/after-login-click.png' });
    }
    
    // Check for input fields
    const inputs = await page.$$('input');
    console.log(`Found ${inputs.length} input fields`);
    
    // Try to find inputs by different methods
    const usernameByPlaceholder = await page.$('input[placeholder*="username" i]');
    const passwordByPlaceholder = await page.$('input[placeholder*="password" i]');
    const usernameByType = await page.$('input[type="text"]');
    const passwordByType = await page.$('input[type="password"]');
    
    console.log('Username by placeholder:', !!usernameByPlaceholder);
    console.log('Password by placeholder:', !!passwordByPlaceholder);
    console.log('Username by type:', !!usernameByType);
    console.log('Password by type:', !!passwordByType);
    
    // Get all input details
    const inputDetails = await page.evaluate(() => {
      const inputs = Array.from(document.querySelectorAll('input'));
      return inputs.map(input => ({
        type: input.type,
        placeholder: input.placeholder,
        ariaLabel: input.getAttribute('aria-label'),
        name: input.name,
        id: input.id,
        visible: input.offsetWidth > 0 && input.offsetHeight > 0
      }));
    });
    
    console.log('Input details:', JSON.stringify(inputDetails, null, 2));
    
  } catch (error) {
    console.error('❌ Error:', error);
    await page.screenshot({ path: 'tests/test-results/currency-debug-error.png' });
  } finally {
    await browser.close();
    console.log('\n✅ Debug completed');
  }
})();