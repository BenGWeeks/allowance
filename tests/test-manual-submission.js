const { chromium } = require('playwright');

async function testManualSubmission() {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext();
  const page = await context.newPage();

  try {
    console.log('🔬 Testing manual form submission...');
    
    // Capture all network requests
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

    // Test 1: Manual create submission
    console.log('\n🧪 Test 1: Manual CREATE submission');
    await page.click('button:has-text("New Allowance")');
    await page.waitForTimeout(2000);

    // Fill form
    await page.fill('input[placeholder*="Weekly allowance"]', 'Manual Test Create');
    await page.fill('input[placeholder*="alice@getalby.com"]', 'manual@test.com');
    await page.fill('input[type="number"]', '77');

    console.log('🔍 Triggering form submission manually...');
    
    // Try different submission methods
    const submissionResult = await page.evaluate(() => {
      const form = document.querySelector('form');
      const button = document.querySelector('button[type="submit"]');
      
      const results = [];
      
      // Method 1: Button click
      if (button) {
        button.click();
        results.push('Button clicked');
      }
      
      return results.join(' | ');
    });
    
    console.log('🧪 Submission triggered:', submissionResult);
    
    // Wait for potential requests
    await page.waitForTimeout(5000);
    
    console.log(`📊 Total API requests captured: ${requests.length}`);
    requests.forEach((req, i) => {
      console.log(`  ${i + 1}. ${req.method} ${req.url}`);
      if (req.postData) {
        console.log(`     Data: ${req.postData.substring(0, 100)}...`);
      }
    });

    // Check if dialog closed (success indicator)
    const dialogClosed = !await page.locator('.q-dialog').isVisible();
    console.log(`📋 Dialog closed: ${dialogClosed}`);

  } catch (error) {
    console.error('❌ Manual submission test failed:', error);
  } finally {
    await browser.close();
  }
}

testManualSubmission();