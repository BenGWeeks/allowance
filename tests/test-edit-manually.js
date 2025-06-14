const { chromium } = require('playwright');

async function testEditManually() {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext();
  const page = await context.newPage();

  try {
    console.log('🧪 Testing edit functionality manually via console...');
    
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
    
    // Check if we can work around the Vue mounting issue by manually creating functionality
    const manualTest = await page.evaluate(() => {
      // Try to access the Vue app through different methods
      const results = [];
      
      if (window.app) {
        results.push('window.app exists');
        
        // Check if we can access data
        if (window.app.$data) {
          results.push('$data accessible');
        } else {
          results.push('$data not accessible');
        }
        
        // Try to find Vue instance on DOM element
        const vueEl = document.querySelector('#vue');
        if (vueEl && vueEl.__vue_app__) {
          results.push('Vue app found on DOM element');
          
          // Try to get the root component
          const rootComponent = vueEl.__vue_app__._instance;
          if (rootComponent && rootComponent.ctx) {
            results.push('Root component context accessible');
            
            // Check for methods
            if (rootComponent.ctx.saveAllowance) {
              results.push('saveAllowance found in context');
              return results.concat(['METHODS_ACCESSIBLE']);
            } else {
              results.push('saveAllowance NOT found in context');
            }
          } else {
            results.push('Root component context not accessible');
          }
        } else {
          results.push('Vue app not found on DOM element');
        }
      } else {
        results.push('window.app does not exist');
      }
      
      return results;
    });
    
    console.log('🔍 Manual Vue access test:', manualTest);
    
    if (manualTest.includes('METHODS_ACCESSIBLE')) {
      console.log('✅ Vue methods are accessible through DOM element!');
      
      // Try to manually trigger edit functionality
      const editTest = await page.evaluate(() => {
        try {
          const vueEl = document.querySelector('#vue');
          const rootComponent = vueEl.__vue_app__._instance;
          
          // Create test allowance data
          const testAllowance = {
            id: 'test-edit-id',
            name: 'Test Edit Allowance',
            wallet: 'default-wallet',
            lightning_address: 'test@edit.com',
            amount: 50,
            currency: 'sats',
            frequency_type: 'weekly',
            start_date: new Date().toISOString().split('T')[0],
            active: true
          };
          
          // Try to call openUpdateDialog
          if (rootComponent.ctx.openUpdateDialog) {
            rootComponent.ctx.openUpdateDialog(testAllowance);
            return 'openUpdateDialog called successfully';
          } else {
            return 'openUpdateDialog not found';
          }
        } catch (error) {
          return `Error: ${error.message}`;
        }
      });
      
      console.log('🧪 Manual edit test result:', editTest);
      
      if (editTest === 'openUpdateDialog called successfully') {
        // Wait and check if dialog opened
        await page.waitForTimeout(2000);
        const dialogVisible = await page.locator('.q-dialog').isVisible();
        console.log('📋 Edit dialog opened:', dialogVisible);
        
        if (dialogVisible) {
          // Try to submit the form manually
          const submitTest = await page.evaluate(() => {
            try {
              const vueEl = document.querySelector('#vue');
              const rootComponent = vueEl.__vue_app__._instance;
              
              if (rootComponent.ctx.saveAllowance) {
                rootComponent.ctx.saveAllowance();
                return 'saveAllowance called successfully';
              } else {
                return 'saveAllowance not found';
              }
            } catch (error) {
              return `Error: ${error.message}`;
            }
          });
          
          console.log('🚀 Manual save test result:', submitTest);
          
          // Wait for API call
          await page.waitForTimeout(3000);
          
          const putRequests = requests.filter(r => r.method === 'PUT');
          console.log(`📊 PUT requests made: ${putRequests.length}`);
          
          if (putRequests.length > 0) {
            console.log('🎉 SUCCESS: Edit functionality works when called manually!');
            console.log('🔍 ISSUE: Vue methods accessible via DOM but not via window.app');
          }
        }
      }
    } else {
      console.log('❌ Vue methods not accessible through any method');
    }

  } catch (error) {
    console.error('❌ Manual edit test failed:', error);
  } finally {
    await browser.close();
  }
}

testEditManually();