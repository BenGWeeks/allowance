const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

(async () => {
  console.log('🎯 Testing currency dropdown population...');
  
  const browser = await chromium.launch({ headless: true, slowMo: 500 });
  const page = await browser.newPage();

  try {
    console.log('🚀 Starting currency dropdown test...');
    
    // Listen for all console messages to debug currency loading
    const consoleMessages = [];
    page.on('console', msg => {
      const message = msg.text();
      consoleMessages.push({type: msg.type(), text: message});
      
      if (msg.type() === 'error') {
        console.log('❌ Browser console error:', message);
      } else if (message.includes('currencies') || message.includes('Currency') || message.includes('Loading')) {
        console.log(`🔍 Browser console ${msg.type()}:`, message);
      }
    });
    
    page.on('pageerror', error => {
      console.log('💥 Page error:', error.message);
    });
    
    // Monitor network requests for currency API calls
    let currencyApiCalled = false;
    let currencyApiResponse = null;
    
    page.on('request', request => {
      if (request.url().includes('/api/v1/currencies')) {
        console.log('📤 Currency API request:', request.url());
        currencyApiCalled = true;
      }
    });
    
    page.on('response', response => {
      if (response.url().includes('/api/v1/currencies')) {
        console.log(`📥 Currency API response: ${response.status()} ${response.url()}`);
        response.json().then(data => {
          currencyApiResponse = data;
          console.log('💰 Currency API returned:', JSON.stringify(data));
        }).catch(err => {
          console.log('❌ Failed to parse currency API response:', err.message);
        });
      }
    });
    
    // Step 1: Login first
    console.log('📝 Step 1: Logging in as admin...');
    await page.goto('http://localhost:5001/');
    await page.waitForLoadState('networkidle');
    
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
    
    // Step 2: Navigate to allowance extension
    console.log('📝 Step 2: Navigating to allowance extension...');
    await page.goto('http://localhost:5001/allowance/');
    await page.waitForTimeout(5000); // Give time for currency API to load
    
    // Step 3: Open the form dialog to access currency dropdown
    console.log('📝 Step 3: Opening form dialog to access currency dropdown...');
    const newAllowanceButton = page.locator('button:has-text("New Allowance")');
    
    if (await newAllowanceButton.isVisible()) {
      await newAllowanceButton.click();
      await page.waitForTimeout(3000); // Wait for form to fully load
      
      // Step 4: Check if currency API was called during page load
      console.log('📝 Step 4: Verifying currency API was called...');
      console.log(`Currency API called: ${currencyApiCalled ? '✅' : '❌'}`);
      
      if (currencyApiCalled && currencyApiResponse) {
        console.log(`Currency API response contains ${currencyApiResponse.length} currencies`);
        console.log('Sample currencies:', currencyApiResponse.slice(0, 10));
      }
      
      // Step 5: Analyze the Vue app state for currencies
      console.log('📝 Step 5: Checking Vue app currency state...');
      const vueState = await page.evaluate(() => {
        const debug = {};
        
        // Check if Vue app is mounted
        const vueEl = document.querySelector('#vue');
        if (vueEl && vueEl.__vue_app__) {
          const instance = vueEl.__vue_app__._instance;
          if (instance && instance.proxy) {
            debug.currencies = instance.proxy.currencies;
            debug.currenciesCount = instance.proxy.currencies ? instance.proxy.currencies.length : 0;
            debug.formDialogData = instance.proxy.formDialog ? instance.proxy.formDialog.data : null;
          }
        }
        
        // Also check window.app if available
        if (window.app) {
          debug.windowAppCurrencies = window.app.currencies;
          debug.windowAppCurrenciesCount = window.app.currencies ? window.app.currencies.length : 0;
        }
        
        return debug;
      });
      
      console.log('🔍 Vue currencies state:', JSON.stringify(vueState, null, 2));
      
      // Step 6: Click the currency dropdown to see available options
      console.log('📝 Step 6: Clicking currency dropdown to see available options...');
      
      // Find and click the currency dropdown
      const currencySelect = page.locator('.q-select').filter({ hasText: 'Currency' });
      await currencySelect.click();
      await page.waitForTimeout(1000); // Wait for dropdown to open
      
      // Get all visible currency options
      const currencyOptions = await page.locator('.q-item').allTextContents();
      console.log(`📋 Currency dropdown shows ${currencyOptions.length} options:`);
      currencyOptions.forEach((option, index) => {
        console.log(`  ${index + 1}. ${option}`);
      });
      
      // Step 7: Verify against expected currencies
      console.log('📝 Step 7: Verifying currency options...');
      
      const expectedBasicCurrencies = ['sats', 'USD', 'EUR'];
      const hasBasicCurrencies = expectedBasicCurrencies.every(currency => 
        currencyOptions.some(option => option.includes(currency))
      );
      
      console.log(`Basic currencies present: ${hasBasicCurrencies ? '✅' : '❌'}`);
      
      // Check if we have more than just the basic currencies
      const hasExtendedCurrencies = currencyOptions.length > 3;
      console.log(`Extended currencies present: ${hasExtendedCurrencies ? '✅' : '❌'}`);
      console.log(`Total currency options: ${currencyOptions.length}`);
      
      // Step 8: Compare with LNBits core API response
      if (currencyApiResponse && currencyApiResponse.length > 0) {
        const expectedCurrencyCount = currencyApiResponse.length + 1; // +1 for 'sats'
        console.log(`Expected currencies from API: ${expectedCurrencyCount}`);
        console.log(`Actually showing in dropdown: ${currencyOptions.length}`);
        
        if (currencyOptions.length >= expectedCurrencyCount) {
          console.log('✅ SUCCESS: Dropdown shows full currency list!');
        } else {
          console.log('❌ FAILURE: Dropdown not showing full currency list');
          console.log('Missing currencies or timing issue detected');
        }
      }
      
      // Step 9: Test specific currencies that should be available
      console.log('📝 Step 9: Testing for specific expected currencies...');
      const commonCurrencies = ['USD', 'EUR', 'GBP', 'JPY', 'AUD', 'CAD', 'CHF'];
      const foundCurrencies = [];
      const missingCurrencies = [];
      
      for (const currency of commonCurrencies) {
        const found = currencyOptions.some(option => 
          option.toUpperCase().includes(currency.toUpperCase())
        );
        if (found) {
          foundCurrencies.push(currency);
        } else {
          missingCurrencies.push(currency);
        }
      }
      
      console.log(`Found common currencies: ${foundCurrencies.join(', ')}`);
      console.log(`Missing common currencies: ${missingCurrencies.join(', ')}`);
      
      // Step 10: Take screenshot for verification
      await page.screenshot({ 
        path: 'tests/test-results/currency-dropdown-test.png', 
        fullPage: true 
      });
      console.log('📸 Screenshot saved to currency-dropdown-test.png');
      
      // Step 11: Save detailed test results
      const testResults = {
        timestamp: new Date().toISOString(),
        currencyApiCalled,
        currencyApiResponse,
        vueState,
        dropdownOptions: currencyOptions,
        foundCurrencies,
        missingCurrencies,
        hasBasicCurrencies,
        hasExtendedCurrencies,
        totalOptions: currencyOptions.length,
        expectedFromApi: currencyApiResponse ? currencyApiResponse.length + 1 : 'unknown',
        consoleMessages: consoleMessages.filter(msg => 
          msg.text.toLowerCase().includes('currency') || 
          msg.text.toLowerCase().includes('loading') ||
          msg.text.toLowerCase().includes('api')
        )
      };
      
      fs.writeFileSync(
        'tests/test-results/currency-dropdown-results.json',
        JSON.stringify(testResults, null, 2)
      );
      console.log('💾 Test results saved to currency-dropdown-results.json');
      
      // Final verdict
      if (hasExtendedCurrencies && currencyOptions.length > 10) {
        console.log('🎉 CURRENCY DROPDOWN TEST PASSED! Full currency list is working!');
        process.exit(0);
      } else {
        console.log('❌ CURRENCY DROPDOWN TEST FAILED! Only showing basic currencies.');
        console.log('This indicates the dynamic currency loading is not working properly.');
        process.exit(1);
      }
      
      // Close dropdown
      await page.keyboard.press('Escape');
      await page.waitForTimeout(500);
      
    } else {
      console.log('❌ New Allowance button not found');
      await page.screenshot({ path: 'tests/test-results/currency-dropdown-no-button.png', fullPage: true });
      process.exit(1);
    }
    
  } catch (error) {
    console.error('💥 Error:', error.message);
    await page.screenshot({ path: 'tests/test-results/currency-dropdown-error.png', fullPage: true });
    process.exit(1);
  } finally {
    await browser.close();
  }
})();