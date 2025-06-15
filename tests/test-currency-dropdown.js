const { chromium } = require('playwright');

/**
 * Test to verify currency dropdown is populated with full list of currencies
 * 
 * This test:
 * 1. Tests the LNbits core /api/v1/currencies endpoint directly
 * 2. Opens the allowance create form and checks currency dropdown
 * 3. Opens the allowance edit form and checks currency dropdown
 * 4. Verifies more than basic currencies (sats, USD, EUR) are available
 * 5. Provides detailed logging for debugging
 */

(async () => {
  console.log('🌍 Starting Currency Dropdown Verification Test...');
  
  const browser = await chromium.launch({ headless: true, slowMo: 500 });
  const page = await browser.newPage();

  try {
    // Listen for console errors and network requests
    page.on('console', msg => {
      if (msg.type() === 'error') {
        console.log('❌ Browser console error:', msg.text());
      }
    });
    
    page.on('pageerror', error => {
      console.log('💥 Page error:', error.message);
    });
    
    // Monitor currency-related API calls
    const apiRequests = [];
    page.on('request', request => {
      if (request.url().includes('/currencies') || request.url().includes('/rate/')) {
        apiRequests.push({
          method: request.method(),
          url: request.url(),
          timestamp: new Date().toISOString()
        });
        console.log(`📤 API Request: ${request.method()} ${request.url()}`);
      }
    });
    
    page.on('response', response => {
      if (response.url().includes('/currencies') || response.url().includes('/rate/')) {
        console.log(`📥 API Response: ${response.status()} ${response.url()}`);
      }
    });

    // Step 1: Test the currencies API endpoint directly
    console.log('📝 Step 1: Testing LNbits core currencies API endpoint...');
    
    await page.goto('http://localhost:5001/');
    await page.waitForLoadState('networkidle');
    
    // Test the endpoint directly via browser
    const apiTestResult = await page.evaluate(async () => {
      try {
        const response = await fetch('/api/v1/currencies');
        const data = await response.json();
        return {
          status: response.status,
          statusText: response.statusText,
          dataType: typeof data,
          isArray: Array.isArray(data),
          length: Array.isArray(data) ? data.length : 'N/A',
          sample: Array.isArray(data) ? data.slice(0, 10) : data,
          error: null
        };
      } catch (error) {
        return {
          status: 'fetch_failed',
          error: error.message
        };
      }
    });
    
    console.log('🔍 Direct API test result:', JSON.stringify(apiTestResult, null, 2));
    
    if (apiTestResult.status === 200) {
      console.log(`✅ API working - found ${apiTestResult.length} currencies`);
      console.log(`📋 Sample currencies:`, apiTestResult.sample);
    } else {
      console.log(`❌ API failed with status: ${apiTestResult.status}`);
    }

    // Step 2: Login
    console.log('📝 Step 2: Logging in...');
    
    // Check if we need to switch to login screen
    const createAccountVisible = await page.locator('text=Create Account').first().isVisible();
    if (createAccountVisible) {
      await page.click('text=Login');
      await page.waitForTimeout(2000);
    }
    
    // Fill login credentials
    await page.fill('input[type="text"], input[type="email"]', 'ben.weeks');
    await page.fill('input[type="password"]', 'zUYmy&05&uZ$3kmf*^T8');
    await page.click('button:has-text("LOGIN")');
    await page.waitForTimeout(3000);

    // Step 3: Navigate to allowance extension
    console.log('📝 Step 3: Navigating to allowance extension...');
    await page.goto('http://localhost:5001/allowance/');
    await page.waitForTimeout(3000);

    // Step 4: Test currency dropdown in CREATE form
    console.log('📝 Step 4: Testing currency dropdown in CREATE form...');
    
    const newAllowanceButton = page.locator('button:has-text("New Allowance")');
    if (await newAllowanceButton.isVisible()) {
      await newAllowanceButton.click();
      await page.waitForTimeout(2000);
      
      // Wait for form to load and Vue app to initialize
      await page.waitForSelector('.q-select', { timeout: 10000 });
      
      // Check Vue currencies data
      const vueCreateCurrencies = await page.evaluate(() => {
        try {
          // Try to access Vue app instance
          const vueEl = document.querySelector('#vue');
          if (vueEl && vueEl.__vue_app__) {
            const app = vueEl.__vue_app__;
            if (app._instance && app._instance.ctx && app._instance.ctx.currencies) {
              return {
                found: true,
                length: app._instance.ctx.currencies.length,
                currencies: app._instance.ctx.currencies.slice(0, 20), // First 20 for debugging
                allCurrencies: app._instance.ctx.currencies
              };
            }
          }
          
          // Fallback: try window.app
          if (window.app && window.app.currencies) {
            return {
              found: true,
              source: 'window.app',
              length: window.app.currencies.length,
              currencies: window.app.currencies.slice(0, 20),
              allCurrencies: window.app.currencies
            };
          }
          
          return { found: false, error: 'No Vue instance or currencies data found' };
        } catch (error) {
          return { found: false, error: error.message };
        }
      });
      
      console.log('🔍 Vue currencies in CREATE form:', JSON.stringify({
        found: vueCreateCurrencies.found,
        length: vueCreateCurrencies.length,
        sample: vueCreateCurrencies.currencies
      }, null, 2));
      
      // Click on currency dropdown to open it
      const currencySelect = page.locator('.q-select').filter({ hasText: 'Currency' });
      await currencySelect.click();
      await page.waitForTimeout(1000);
      
      // Get all dropdown options
      const createDropdownOptions = await page.locator('.q-item').allTextContents();
      console.log('📋 CREATE form dropdown options:', createDropdownOptions);
      console.log(`📊 CREATE form: Found ${createDropdownOptions.length} currency options`);
      
      // Check if we have more than the basic 3 currencies
      const hasMoreThanBasic = createDropdownOptions.length > 3;
      const hasBasicCurrencies = ['sats', 'USD', 'EUR'].every(currency => 
        createDropdownOptions.some(option => option.includes(currency))
      );
      
      console.log(`✅ Has basic currencies (sats, USD, EUR): ${hasBasicCurrencies}`);
      console.log(`✅ Has more than 3 options: ${hasMoreThanBasic}`);
      
      // Close dropdown by pressing Escape
      await page.keyboard.press('Escape');
      await page.waitForTimeout(500);
      
      // Close create dialog
      await page.locator('button:has-text("Cancel")').click();
      await page.waitForTimeout(1000);
      
      // Store create form results
      const createFormResults = {
        vueData: vueCreateCurrencies,
        dropdownOptions: createDropdownOptions,
        hasMoreThanBasic: hasMoreThanBasic,
        hasBasicCurrencies: hasBasicCurrencies
      };

      // Step 5: Test currency dropdown in EDIT form (if allowances exist)
      console.log('📝 Step 5: Testing currency dropdown in EDIT form...');
      
      const allowanceRows = page.locator('.q-table tbody tr');
      const rowCount = await allowanceRows.count();
      
      if (rowCount > 0) {
        console.log(`📋 Found ${rowCount} existing allowances`);
        
        // Click edit on first allowance
        const firstEditButton = allowanceRows.first().locator('button:has([class*="edit"]), button:has([name="edit"]), .q-btn:has(.q-icon[aria-label="edit"])').first();
        await firstEditButton.click();
        await page.waitForTimeout(2000);
        
        // Check Vue currencies data in edit form
        const vueEditCurrencies = await page.evaluate(() => {
          try {
            const vueEl = document.querySelector('#vue');
            if (vueEl && vueEl.__vue_app__) {
              const app = vueEl.__vue_app__;
              if (app._instance && app._instance.ctx && app._instance.ctx.currencies) {
                return {
                  found: true,
                  length: app._instance.ctx.currencies.length,
                  currencies: app._instance.ctx.currencies.slice(0, 20)
                };
              }
            }
            
            if (window.app && window.app.currencies) {
              return {
                found: true,
                source: 'window.app',
                length: window.app.currencies.length,
                currencies: window.app.currencies.slice(0, 20)
              };
            }
            
            return { found: false, error: 'No Vue instance or currencies data found' };
          } catch (error) {
            return { found: false, error: error.message };
          }
        });
        
        console.log('🔍 Vue currencies in EDIT form:', JSON.stringify({
          found: vueEditCurrencies.found,
          length: vueEditCurrencies.length,
          sample: vueEditCurrencies.currencies
        }, null, 2));
        
        // Click on currency dropdown in edit form
        const editCurrencySelect = page.locator('.q-select').filter({ hasText: 'Currency' });
        await editCurrencySelect.click();
        await page.waitForTimeout(1000);
        
        // Get all dropdown options in edit form
        const editDropdownOptions = await page.locator('.q-item').allTextContents();
        console.log('📋 EDIT form dropdown options:', editDropdownOptions);
        console.log(`📊 EDIT form: Found ${editDropdownOptions.length} currency options`);
        
        const editHasMoreThanBasic = editDropdownOptions.length > 3;
        const editHasBasicCurrencies = ['sats', 'USD', 'EUR'].every(currency => 
          editDropdownOptions.some(option => option.includes(currency))
        );
        
        console.log(`✅ EDIT - Has basic currencies: ${editHasBasicCurrencies}`);
        console.log(`✅ EDIT - Has more than 3 options: ${editHasMoreThanBasic}`);
        
        // Close dropdown and dialog
        await page.keyboard.press('Escape');
        await page.waitForTimeout(500);
        await page.locator('button:has-text("Cancel")').click();
        await page.waitForTimeout(1000);
        
        // Store edit form results
        const editFormResults = {
          vueData: vueEditCurrencies,
          dropdownOptions: editDropdownOptions,
          hasMoreThanBasic: editHasMoreThanBasic,
          hasBasicCurrencies: editHasBasicCurrencies
        };
        
        // Final evaluation
        console.log('\n🎯 FINAL TEST RESULTS:');
        console.log('='.repeat(50));
        
        console.log(`📊 LNbits API Status: ${apiTestResult.status === 200 ? '✅ Working' : '❌ Failed'}`);
        console.log(`📊 API Currency Count: ${apiTestResult.length || 'Unknown'}`);
        
        console.log(`📊 CREATE Form Vue Data: ${createFormResults.vueData.found ? '✅ Found' : '❌ Missing'}`);
        console.log(`📊 CREATE Form Currency Count: ${createFormResults.vueData.length || 'Unknown'}`);
        console.log(`📊 CREATE Form Dropdown Options: ${createFormResults.dropdownOptions.length}`);
        console.log(`📊 CREATE Form Has Full List: ${createFormResults.hasMoreThanBasic ? '✅ Yes' : '❌ No'}`);
        
        console.log(`📊 EDIT Form Vue Data: ${editFormResults.vueData.found ? '✅ Found' : '❌ Missing'}`);
        console.log(`📊 EDIT Form Currency Count: ${editFormResults.vueData.length || 'Unknown'}`);
        console.log(`📊 EDIT Form Dropdown Options: ${editFormResults.dropdownOptions.length}`);
        console.log(`📊 EDIT Form Has Full List: ${editFormResults.hasMoreThanBasic ? '✅ Yes' : '❌ No'}`);
        
        console.log('\n📋 All API Requests Made:');
        apiRequests.forEach(req => {
          console.log(`   ${req.method} ${req.url}`);
        });
        
        // Determine overall test result
        const apiWorking = apiTestResult.status === 200 && apiTestResult.length > 3;
        const createFormWorking = createFormResults.hasMoreThanBasic;
        const editFormWorking = editFormResults.hasMoreThanBasic;
        
        const testPassed = apiWorking && createFormWorking && editFormWorking;
        
        if (testPassed) {
          console.log('\n🎉 CURRENCY DROPDOWN TEST PASSED! 🎉');
          console.log('✅ API is working and returns full currency list');
          console.log('✅ CREATE form shows full currency list in dropdown');
          console.log('✅ EDIT form shows full currency list in dropdown');
          await page.screenshot({ path: 'tests/test-results/currency-dropdown-success.png', fullPage: true });
          process.exit(0);
        } else {
          console.log('\n❌ CURRENCY DROPDOWN TEST FAILED!');
          console.log(`❌ API working: ${apiWorking}`);
          console.log(`❌ CREATE form working: ${createFormWorking}`);
          console.log(`❌ EDIT form working: ${editFormWorking}`);
          
          if (!apiWorking) {
            console.log('🔧 Issue: LNbits core /api/v1/currencies endpoint is not returning expected data');
          }
          if (!createFormWorking) {
            console.log('🔧 Issue: CREATE form currency dropdown only shows basic currencies');
          }
          if (!editFormWorking) {
            console.log('🔧 Issue: EDIT form currency dropdown only shows basic currencies');
          }
          
          await page.screenshot({ path: 'tests/test-results/currency-dropdown-failed.png', fullPage: true });
          process.exit(1);
        }
        
      } else {
        console.log('⚠️ No allowances found for edit form testing');
        console.log('🎯 Testing CREATE form only...');
        
        const testPassed = apiTestResult.status === 200 && createFormResults.hasMoreThanBasic;
        
        if (testPassed) {
          console.log('\n🎉 CURRENCY DROPDOWN TEST PASSED (CREATE ONLY)! 🎉');
          process.exit(0);
        } else {
          console.log('\n❌ CURRENCY DROPDOWN TEST FAILED!');
          console.log(`❌ API working: ${apiTestResult.status === 200}`);
          console.log(`❌ CREATE form working: ${createFormResults.hasMoreThanBasic}`);
          process.exit(1);
        }
      }
      
    } else {
      console.log('❌ New Allowance button not found');
      await page.screenshot({ path: 'tests/test-results/currency-dropdown-no-button.png', fullPage: true });
      process.exit(1);
    }
    
  } catch (error) {
    console.error('💥 Currency dropdown test error:', error.message);
    await page.screenshot({ path: 'tests/test-results/currency-dropdown-error.png', fullPage: true });
    process.exit(1);
  } finally {
    await browser.close();
  }
})();