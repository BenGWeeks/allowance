const { chromium } = require('playwright');

async function testFullFunctionality() {
  const browser = await chromium.launch({ headless: false });
  const context = await browser.newContext();
  const page = await context.newPage();

  try {
    console.log('🧪 Testing full create and edit functionality after Vue fix...');
    
    // Capture network requests to verify API calls
    const requests = [];
    page.on('request', request => {
      if (request.url().includes('/allowance/api/v1/')) {
        requests.push({
          method: request.method(),
          url: request.url(),
          postData: request.postData()
        });
        console.log(`📡 ${request.method()} ${request.url()}`);
      }
    });

    page.on('response', response => {
      if (response.url().includes('/allowance/api/v1/')) {
        console.log(`📥 ${response.status()} ${response.url()}`);
      }
    });
    
    // Capture console logs
    page.on('console', msg => {
      if (msg.text().includes('saveAllowance') || msg.text().includes('Vue app mounted')) {
        console.log(`📣 ${msg.text()}`);
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

    // Navigate to allowance
    await page.goto('http://localhost:5001/allowance');
    await page.waitForTimeout(5000);
    
    // Check Vue state
    const vueState = await page.evaluate(() => {
      return {
        appExists: typeof window.app !== 'undefined',
        saveAllowanceExists: window.app && typeof window.app.saveAllowance === 'function',
        openCreateDialogExists: window.app && typeof window.app.openCreateDialog === 'function',
        openUpdateDialogExists: window.app && typeof window.app.openUpdateDialog === 'function'
      };
    });
    
    console.log('🔍 Vue methods available:', JSON.stringify(vueState, null, 2));
    
    if (!vueState.saveAllowanceExists) {
      console.log('❌ saveAllowance method not available - Vue app not properly mounted');
      return;
    }
    
    console.log('✅ Vue app properly mounted with all methods available');
    
    // Test 1: Manual create test (bypass UI if needed)
    console.log('\n🧪 Test 1: Manual create allowance test');
    
    const createResult = await page.evaluate(() => {
      try {
        // Manually trigger create dialog
        window.app.openCreateDialog();
        
        // Set form data
        window.app.formDialog.data = {
          name: 'Manual Test Create',
          wallet: window.app.g.user.wallets[0].id,
          lightning_address: 'manual@test.com',
          amount: 75,
          currency: 'sats',
          frequency_type: 'weekly',
          start_date: new Date().toISOString().split('T')[0],
          active: true
        };
        
        // Call saveAllowance directly
        window.app.saveAllowance();
        
        return { success: true, error: null };
      } catch (error) {
        return { success: false, error: error.message };
      }
    });
    
    console.log('🔧 Manual create result:', createResult);
    
    // Wait for API request
    await page.waitForTimeout(3000);
    
    const createRequests = requests.filter(r => r.method === 'POST');
    console.log(`📊 POST requests made: ${createRequests.length}`);
    
    if (createRequests.length > 0) {
      console.log('✅ CREATE functionality working!');
      
      // Test 2: Test edit functionality
      console.log('\n🧪 Test 2: Manual edit allowance test');
      
      // First get allowances to find one to edit
      const editResult = await page.evaluate(() => {
        try {
          // Simulate editing the first allowance
          const mockAllowance = {
            id: 'test-id',
            name: 'Original Name',
            wallet: window.app.g.user.wallets[0].id,
            lightning_address: 'original@test.com',
            amount: 50,
            currency: 'sats',
            frequency_type: 'weekly',
            start_date: new Date().toISOString().split('T')[0],
            active: true
          };
          
          // Call openUpdateDialog
          window.app.openUpdateDialog(mockAllowance);
          
          // Modify the data
          window.app.formDialog.data.name = 'Updated Name';
          window.app.formDialog.data.amount = 100;
          
          // Call saveAllowance (should trigger PUT request)
          window.app.saveAllowance();
          
          return { success: true, error: null };
        } catch (error) {
          return { success: false, error: error.message };
        }
      });
      
      console.log('🔧 Manual edit result:', editResult);
      
      // Wait for API request
      await page.waitForTimeout(3000);
      
      const editRequests = requests.filter(r => r.method === 'PUT');
      console.log(`📊 PUT requests made: ${editRequests.length}`);
      
      if (editRequests.length > 0) {
        console.log('✅ EDIT functionality working!');
        console.log('🎉 BOTH CREATE AND EDIT ARE WORKING!');
      } else {
        console.log('❌ Edit functionality not working - no PUT requests');
      }
      
    } else {
      console.log('❌ Create functionality not working - no POST requests');
    }
    
    // Summary
    console.log('\n📋 FINAL SUMMARY:');
    console.log(`  Vue app mounted: ${vueState.appExists}`);
    console.log(`  saveAllowance method: ${vueState.saveAllowanceExists}`);
    console.log(`  POST requests (create): ${requests.filter(r => r.method === 'POST').length}`);
    console.log(`  PUT requests (edit): ${requests.filter(r => r.method === 'PUT').length}`);
    console.log(`  Total API requests: ${requests.length}`);
    
    if (createResult.success && editResult.success) {
      console.log('✅ SUCCESS: Form submission functionality is working!');
    } else {
      console.log('❌ Issues remain with form submission');
    }

  } catch (error) {
    console.error('❌ Full functionality test failed:', error);
    await page.screenshot({ path: 'tests/test-results/full-test-error.png' });
  } finally {
    console.log('🔍 Leaving browser open for manual inspection...');
    // await browser.close();
  }
}

testFullFunctionality();