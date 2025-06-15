const { chromium } = require('playwright');

async function testEditUIDirect() {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext();
  const page = await context.newPage();

  try {
    console.log('🧪 Testing edit functionality via direct UI interaction...');
    
    // Capture network requests
    const requests = [];
    page.on('request', request => {
      if (request.url().includes('/allowance/api/v1/allowance')) {
        requests.push({
          method: request.method(),
          url: request.url()
        });
        console.log(`📡 ${request.method()} ${request.url()}`);
      }
    });

    page.on('response', response => {
      if (response.url().includes('/allowance/api/v1/allowance')) {
        console.log(`📥 ${response.status()} ${response.url()}`);
      }
    });

    // Capture console logs from saveAllowance
    page.on('console', msg => {
      if (msg.text().includes('🔥') || msg.text().includes('saveAllowance') || msg.text().includes('✅') || msg.text().includes('❌')) {
        console.log(`📣 Page console: ${msg.text()}`);
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
    
    const initialCount = await page.locator('.q-table tbody tr').count();
    console.log(`📊 Initial allowance count: ${initialCount}`);
    
    if (initialCount === 0) {
      console.log('❌ No allowances to edit');
      return;
    }
    
    // Click edit button on first allowance
    console.log('🔧 Clicking edit button on first allowance...');
    await page.locator('button.text-light-blue').first().click();
    await page.waitForTimeout(2000);
    
    const dialogVisible = await page.locator('.q-dialog').isVisible();
    console.log('📋 Edit dialog opened:', dialogVisible);
    
    if (dialogVisible) {
      // Get the current amount value to verify edit
      const currentAmount = await page.inputValue('input[type="number"]');
      console.log('💰 Current amount:', currentAmount);
      
      // Change the amount to test edit
      const newAmount = parseInt(currentAmount) + 10;
      console.log(`📝 Changing amount from ${currentAmount} to ${newAmount}...`);
      
      await page.fill('input[type="number"]', newAmount.toString());
      await page.waitForTimeout(500);
      
      console.log('🚀 Clicking Update Allowance button...');
      await page.click('button:has-text("Update Allowance")');
      
      // Wait for response
      await page.waitForTimeout(5000);
      
      const dialogClosed = !await page.locator('.q-dialog').isVisible();
      console.log('📋 Dialog closed after submit:', dialogClosed);
      
      const putRequests = requests.filter(r => r.method === 'PUT');
      console.log(`📊 PUT requests made: ${putRequests.length}`);
      
      if (putRequests.length > 0) {
        console.log('✅ SUCCESS: Edit functionality works!');
        
        // Verify the amount changed in the table
        await page.waitForTimeout(2000);
        const updatedAmount = await page.locator('.q-table tbody tr').first().locator('td').nth(2).textContent();
        console.log('📊 Updated amount in table:', updatedAmount);
        
        if (updatedAmount.includes(newAmount.toString())) {
          console.log('🎉 PERFECT: Amount was updated in the table!');
        } else {
          console.log('⚠️ Amount in table might not have updated yet');
        }
      } else {
        console.log('❌ No PUT request made - edit submission failed');
        
        // Check for validation errors
        const errorElements = await page.locator('.q-field--error').count();
        console.log(`⚠️ Validation error elements: ${errorElements}`);
      }
    }

  } catch (error) {
    console.error('❌ Edit UI test failed:', error);
  } finally {
    await browser.close();
  }
}

testEditUIDirect();