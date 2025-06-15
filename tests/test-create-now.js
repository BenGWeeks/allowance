const { chromium } = require('playwright');

async function testCreateNow() {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext();
  const page = await context.newPage();

  try {
    console.log('🧪 Testing create functionality right now...');
    
    // Capture network requests
    const requests = [];
    page.on('request', request => {
      if (request.url().includes('/allowance/api/v1/')) {
        requests.push({
          method: request.method(),
          url: request.url()
        });
        console.log(`📡 ${request.method()} ${request.url()}`);
      }
    });

    page.on('response', response => {
      if (response.url().includes('/allowance/api/v1/')) {
        console.log(`📥 ${response.status()} ${response.url()}`);
      }
    });
    
    // Login
    await page.goto('http://localhost:5001/');
    await page.waitForLoadState('networkidle');
    
    const createAccountVisible = await page.locator('text=Create Account').first().isVisible();
    if (createAccountVisible) {
      await page.click('text=Login');
      await page.waitForTimeout(2000);
    }
    
    await page.fill('input[type="text"], input[type="email"]', 'ben.weeks');
    await page.fill('input[type="password"]', 'zUYmy&05&uZ$3kmf*^T8');
    await page.click('button:has-text("LOGIN")');
    await page.waitForTimeout(3000);

    await page.goto('http://localhost:5001/allowance');
    await page.waitForTimeout(3000);
    
    // Check initial count
    const initialCount = await page.locator('.q-table tbody tr').count();
    console.log(`📊 Initial allowance count: ${initialCount}`);
    
    console.log('🔄 Clicking New Allowance button...');
    await page.click('button:has-text("New Allowance")');
    await page.waitForTimeout(2000);
    
    const dialogVisible = await page.locator('.q-dialog').isVisible();
    console.log('📋 Create dialog opened:', dialogVisible);
    
    if (dialogVisible) {
      console.log('📝 Filling create form...');
      
      // Fill form with unique data to verify it works
      const timestamp = Date.now();
      
      await page.fill('input[placeholder*="Weekly allowance"]', `Test Create ${timestamp}`);
      await page.fill('input[placeholder*="alice@getalby.com"]', `test${timestamp}@example.com`);
      await page.fill('input[type="number"]', '77');
      
      console.log('🚀 Submitting create form...');
      await page.click('button[type="submit"]');
      
      // Wait for response
      await page.waitForTimeout(5000);
      
      const dialogClosed = !await page.locator('.q-dialog').isVisible();
      console.log('📋 Dialog closed after submit:', dialogClosed);
      
      const postRequests = requests.filter(r => r.method === 'POST');
      console.log(`📊 POST requests made: ${postRequests.length}`);
      
      if (postRequests.length > 0) {
        console.log('✅ CREATE IS WORKING! POST request was made');
        
        // Check if count increased
        await page.waitForTimeout(2000);
        const newCount = await page.locator('.q-table tbody tr').count();
        console.log(`📊 New allowance count: ${newCount}`);
        
        if (newCount > initialCount) {
          console.log('🎉 SUCCESS: New allowance appears in table!');
          console.log('🔍 This proves Vue app IS working for create operations');
        } else {
          console.log('⚠️ POST request made but count didn\'t increase (possible error)');
        }
      } else {
        console.log('❌ No POST request made - create submission failed');
      }
    }

  } catch (error) {
    console.error('❌ Create test failed:', error);
  } finally {
    await browser.close();
  }
}

testCreateNow();