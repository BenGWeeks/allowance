const { chromium } = require('playwright');

async function testActualSubmitClick() {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext();
  const page = await context.newPage();

  try {
    console.log('🧪 Testing actual form submit button click...');
    
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

    // Capture console logs from the page
    page.on('console', msg => {
      if (msg.text().includes('saveAllowance') || msg.text().includes('🔥') || msg.text().includes('🔍') || msg.text().includes('✅') || msg.text().includes('❌')) {
        console.log(`📣 Page console: ${msg.text()}`);
      }
    });

    // Capture page errors
    page.on('pageerror', error => {
      console.log(`💥 Page error: ${error.message}`);
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
    
    const initialCount = await page.locator('.q-table tbody tr').count();
    console.log(`📊 Initial allowance count: ${initialCount}`);
    
    console.log('🔄 Clicking New Allowance button...');
    await page.click('button:has-text("New Allowance")');
    await page.waitForTimeout(2000);
    
    const dialogVisible = await page.locator('.q-dialog').isVisible();
    console.log('📋 Create dialog opened:', dialogVisible);
    
    if (dialogVisible) {
      console.log('📝 Filling form fields...');
      
      // Fill form with unique data  
      const timestamp = Date.now();
      
      await page.fill('input[placeholder*="Weekly allowance"]', `Submit Test ${timestamp}`);
      await page.fill('input[placeholder*="alice@getalby.com"]', `submit${timestamp}@test.com`);
      await page.fill('input[type="number"]', '99');
      
      console.log('📝 All required fields filled (frequency has default)');
      
      console.log('🚀 Clicking submit button directly...');
      
      // Click the submit button (now using @click handler)
      await page.click('button:has-text("Create Allowance")');
      
      // Wait for any response
      await page.waitForTimeout(5000);
      
      const dialogClosed = !await page.locator('.q-dialog').isVisible();
      console.log('📋 Dialog closed after submit:', dialogClosed);
      
      const postRequests = requests.filter(r => r.method === 'POST');
      console.log(`📊 POST requests made: ${postRequests.length}`);
      
      if (postRequests.length > 0) {
        console.log('✅ SUCCESS: Form submission works with direct button click!');
        
        // Check if count increased
        const newCount = await page.locator('.q-table tbody tr').count();
        console.log(`📊 New allowance count: ${newCount}`);
        
        if (newCount > initialCount) {
          console.log('🎉 NEW ALLOWANCE CREATED! Vue form submission is working!');
        }
      } else {
        console.log('❌ No POST request - form submission still failed');
        
        // Check for validation errors
        const errorElements = await page.locator('.q-field--error').count();
        console.log(`⚠️ Validation error elements: ${errorElements}`);
        
        if (errorElements > 0) {
          const errorTexts = await page.locator('.q-field--error').allTextContents();
          console.log('❌ Validation errors:', errorTexts);
        }
      }
    }

  } catch (error) {
    console.error('❌ Submit click test failed:', error);
  } finally {
    await browser.close();
  }
}

testActualSubmitClick();