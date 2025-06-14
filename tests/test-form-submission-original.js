const { chromium } = require('playwright');

async function testFormSubmissionOriginal() {
  const browser = await chromium.launch({ headless: false });
  const context = await browser.newContext();
  const page = await context.newPage();

  try {
    console.log('🧪 Testing form submission with original HEAD version...');
    
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
    
    // Check if UI is working
    const newAllowanceBtn = await page.locator('button:has-text("New Allowance")').count();
    console.log('✅ New Allowance button found:', newAllowanceBtn > 0);
    
    if (newAllowanceBtn > 0) {
      console.log('🔄 Clicking New Allowance button...');
      await page.click('button:has-text("New Allowance")');
      await page.waitForTimeout(2000);
      
      const dialog = page.locator('.q-dialog');
      const dialogVisible = await dialog.isVisible();
      console.log('✅ Dialog opened:', dialogVisible);
      
      if (dialogVisible) {
        console.log('📝 Filling form...');
        
        // Fill required fields
        await page.fill('input[placeholder*="Weekly allowance"]', 'Original Test');
        await page.fill('input[placeholder*="alice@getalby.com"]', 'original@test.com');
        await page.fill('input[type="number"]', '123');
        
        console.log('🚀 Submitting form...');
        await page.click('button[type="submit"]');
        
        // Wait for response
        await page.waitForTimeout(5000);
        
        const dialogClosed = !await dialog.isVisible();
        console.log('✅ Dialog closed:', dialogClosed);
        
        console.log(`📊 API requests made: ${requests.length}`);
        const postRequests = requests.filter(r => r.method === 'POST');
        console.log(`📊 POST requests (create): ${postRequests.length}`);
        
        if (postRequests.length > 0 && dialogClosed) {
          console.log('🎉 SUCCESS: Form submission works with original version!');
        } else if (postRequests.length > 0) {
          console.log('⚠️ PARTIAL: API called but dialog still open (validation error?)');
        } else {
          console.log('❌ FAILED: No POST request made - form submission not working');
          
          // Check Vue app state
          const vueState = await page.evaluate(() => {
            return {
              appExists: typeof window.app !== 'undefined',
              saveAllowanceAccessible: window.app && typeof window.app.saveAllowance === 'function'
            };
          });
          console.log('🔍 Vue state:', vueState);
        }
      }
    }

  } catch (error) {
    console.error('❌ Form submission test failed:', error);
  } finally {
    console.log('🔍 Leaving browser open for inspection...');
    // await browser.close();
  }
}

testFormSubmissionOriginal();