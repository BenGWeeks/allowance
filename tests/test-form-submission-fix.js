const { chromium } = require('playwright');

async function testFormSubmissionFix() {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext();
  const page = await context.newPage();

  try {
    console.log('🔬 Testing form submission after Vue mount fix...');
    
    // Capture network requests
    const requests = [];
    page.on('request', request => {
      if (request.url().includes('/allowance/api/v1/')) {
        requests.push({
          method: request.method(),
          url: request.url(),
          postData: request.postData()
        });
        console.log(`📡 Request: ${request.method()} ${request.url()}`);
      }
    });

    page.on('response', response => {
      if (response.url().includes('/allowance/api/v1/')) {
        console.log(`📥 Response: ${response.status()} ${response.url()}`);
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

    // Test create form
    console.log('\n🧪 Test 1: CREATE form submission');
    await page.click('button:has-text("New Allowance")');
    await page.waitForTimeout(2000);

    // Check if Vue app is now accessible
    const vueAccessible = await page.evaluate(() => {
      return {
        windowApp: typeof window.app !== 'undefined',
        saveAllowance: window.app && typeof window.app.saveAllowance === 'function',
        vueElement: !!document.querySelector('#vue')?.__vue_app__
      };
    });
    
    console.log('✅ Vue accessibility:', JSON.stringify(vueAccessible, null, 2));

    // Fill form
    await page.fill('input[placeholder*="Weekly allowance"]', 'Vue Fix Test');
    await page.fill('input[placeholder*="alice@getalby.com"]', 'vuefix@test.com');
    await page.fill('input[type="number"]', '25');

    console.log('🔍 Clicking submit button...');
    await page.click('button[type="submit"]');
    
    // Wait for request
    await page.waitForTimeout(5000);
    
    console.log(`📊 Total API requests captured: ${requests.length}`);
    requests.forEach((req, i) => {
      console.log(`  ${i + 1}. ${req.method} ${req.url}`);
      if (req.postData) {
        console.log(`     Data: ${req.postData.substring(0, 200)}...`);
      }
    });

    // Check if dialog closed (success indicator)
    const dialogClosed = !await page.locator('.q-dialog').isVisible();
    console.log(`📋 Dialog closed: ${dialogClosed}`);
    
    if (dialogClosed && requests.some(r => r.method === 'POST')) {
      console.log('✅ Form submission appears to be working!');
    } else {
      console.log('❌ Form submission still not working');
    }

  } catch (error) {
    console.error('❌ Form submission test failed:', error);
  } finally {
    await browser.close();
  }
}

testFormSubmissionFix();