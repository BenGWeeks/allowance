const { test, expect } = require('@playwright/test');

test('Screenshot table without ID column', async ({ page }) => {
  console.log('🚀 Starting screenshot test for table without ID column');
  
  try {
    // Navigate to the initial page
    await page.goto('http://localhost:5000');
    console.log('📍 Navigated to localhost:5000');
    
    // Wait for page to load
    await page.waitForLoadState('networkidle');
    
    // Check if we're on the create account screen
    const setupText = await page.textContent('body').catch(() => '');
    
    if (setupText.includes('Set up the Superuser account below.')) {
      console.log('🔧 Setting up superuser account...');
      await page.fill('[aria-label="Username"]', 'admin');
      await page.fill('[aria-label="Password"]', 'password');
      await page.click('button[type="submit"]');
      await page.waitForTimeout(2000);
    }
    
    // Check if we need to login
    const currentUrl = page.url();
    if (currentUrl.includes('/login') || setupText.includes('Login')) {
      console.log('🔐 Logging in...');
      await page.fill('[aria-label="Username"]', 'admin');
      await page.fill('[aria-label="Password"]', 'password');
      await page.click('button[type="submit"]');
      await page.waitForTimeout(2000);
    }
    
    // Navigate to extensions page
    console.log('🔌 Navigating to extensions...');
    await page.click('a[href="/extensions"]');
    await page.waitForTimeout(1000);
    
    // Find and click the allowance extension
    console.log('🎯 Finding Allowance extension...');
    const allowanceCard = page.locator('.q-card:has(.text-h5:has-text("Allowance"))');
    await allowanceCard.waitFor({ timeout: 10000 });
    
    // Click on the extension (not the enable button)
    await allowanceCard.click();
    await page.waitForTimeout(2000);
    
    // Wait for the allowance page to load
    console.log('⏳ Waiting for allowance page...');
    await page.waitForSelector('[data-cy="allowance-extension"]', { timeout: 10000 });
    
    // Check if there are any existing allowances in the table
    const tableExists = await page.locator('.q-table').isVisible();
    
    if (tableExists) {
      console.log('📊 Table found, taking screenshot...');
      
      // Take screenshot of the table area
      await page.screenshot({ 
        path: 'tests/test-results/table-without-id-column.png',
        fullPage: true
      });
      
      console.log('✅ Screenshot saved: table-without-id-column.png');
      
      // Also take a focused screenshot of just the table
      const table = page.locator('.q-table');
      await table.screenshot({ 
        path: 'tests/test-results/table-without-id-column-focused.png'
      });
      
      console.log('✅ Focused screenshot saved: table-without-id-column-focused.png');
      
    } else {
      console.log('⚠️ No table found, creating a test allowance first...');
      
      // Create a test allowance to show the table
      await page.click('[data-cy="new-allowance-btn"]');
      await page.waitForTimeout(1000);
      
      // Fill the form
      await page.fill('input[aria-label="Description *"]', 'Test Allowance');
      await page.fill('input[aria-label="Lightning Address *"]', 'test@example.com');
      await page.fill('input[aria-label="Amount *"]', '100');
      
      // Set frequency
      await page.click('.q-select');
      await page.click('.q-item:has-text("Weekly")');
      
      // Set date
      const today = new Date().toISOString().split('T')[0];
      await page.fill('input[type="date"]', today);
      
      // Submit form
      await page.click('button[type="submit"]');
      await page.waitForTimeout(2000);
      
      // Now take screenshot
      await page.screenshot({ 
        path: 'tests/test-results/table-without-id-column.png',
        fullPage: true
      });
      
      console.log('✅ Screenshot saved after creating test allowance');
    }
    
    console.log('🎉 Test completed successfully');
    process.exit(0);
    
  } catch (error) {
    console.error('❌ Test failed:', error);
    await page.screenshot({ path: 'tests/test-results/screenshot-error.png', fullPage: true });
    process.exit(1);
  }
});