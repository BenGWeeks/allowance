const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

(async () => {
  console.log('🎯 Testing currency dropdown population...');
  
  const browser = await chromium.launch({ headless: true, slowMo: 500 });
  const page = await browser.newPage();

  try {
    console.log('🚀 Starting currency dropdown test...');
    
    // Listen for console errors and network requests
    page.on('console', msg => {
      if (msg.type() === 'error') {
        console.log('❌ Browser console error:', msg.text());
      }
    });
    
    page.on('pageerror', error => {
      console.log('💥 Page error:', error.message);
    });
    
    // Monitor currency API requests
    page.on('request', request => {
      if (request.url().includes('/api/v1/currencies')) {
        console.log('📤 Currency API request:', request.url(), request.method());
      }
    });
    
    page.on('response', response => {
      if (response.url().includes('/api/v1/currencies')) {
        console.log(`📥 Currency API response: ${response.status()} ${response.url()}`);
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
    await page.waitForTimeout(3000);
    
    // Step 3: Test currency API directly first
    console.log('📝 Step 3: Testing currency API directly...');
    
    // Test core LNBits currencies endpoint
    const coreApiResponse = await page.evaluate(async () => {
      try {
        const response = await fetch('/api/v1/currencies');
        const data = await response.json();
        return { success: true, data: data, status: response.status };
      } catch (error) {
        return { success: false, error: error.message };
      }
    });
    
    console.log('🌍 Core LNBits currencies API result:', JSON.stringify(coreApiResponse, null, 2));
    
    // Test extension currencies endpoint
    const extensionApiResponse = await page.evaluate(async () => {
      try {
        const response = await fetch('/allowance/api/v1/currencies');
        const data = await response.json();
        return { success: true, data: data, status: response.status };
      } catch (error) {
        return { success: false, error: error.message };
      }
    });
    
    console.log('🔌 Extension currencies API result:', JSON.stringify(extensionApiResponse, null, 2));
    
    // Step 4: Check Vue app currencies data
    console.log('📝 Step 4: Checking Vue app currencies...');
    
    // Wait for Vue app to load
    await page.waitForTimeout(2000);
    
    const vueAppCurrencies = await page.evaluate(() => {
      try {
        if (window.app && window.app.currencies) {
          return {
            success: true,
            currencies: window.app.currencies,
            currencyCount: window.app.currencies.length
          };
        }
        return { success: false, error: 'Vue app or currencies not found' };
      } catch (error) {
        return { success: false, error: error.message };
      }
    });
    
    console.log('⚛️ Vue app currencies:', JSON.stringify(vueAppCurrencies, null, 2));
    
    // Step 5: Open the allowance form and check dropdown
    console.log('📝 Step 5: Opening allowance form to test dropdown...');
    
    const newAllowanceButton = page.locator('button:has-text("New Allowance")');
    
    if (await newAllowanceButton.isVisible()) {
      await newAllowanceButton.click();
      await page.waitForTimeout(2000);
      
      // Step 6: Check currency dropdown options
      console.log('📝 Step 6: Analyzing currency dropdown options...');
      
      // Wait for form to load
      await page.waitForSelector('.q-select', { timeout: 10000 });
      
      // Find the currency dropdown
      const currencySelect = page.locator('.q-select').filter({ hasText: 'Currency' });
      
      if (await currencySelect.isVisible()) {
        // Click to open the dropdown
        await currencySelect.click();
        await page.waitForTimeout(1000);
        
        // Get all dropdown options
        const dropdownOptions = await page.locator('.q-item').allTextContents();
        console.log('📋 Currency dropdown options:', dropdownOptions);
        
        // Count the options
        const optionCount = dropdownOptions.length;
        console.log(`📊 Total currency options found: ${optionCount}`);
        
        // Check if we have more than just the basic 3 currencies
        const hasBasicOnly = optionCount <= 3 && 
                            dropdownOptions.some(opt => opt.includes('sats') || opt.includes('USD') || opt.includes('EUR'));
        
        const hasExtendedCurrencies = optionCount > 3;
        
        console.log(`🔍 Analysis:`);
        console.log(`  - Basic currencies only (sats/USD/EUR): ${hasBasicOnly ? '✅' : '❌'}`);
        console.log(`  - Extended currencies (>3 options): ${hasExtendedCurrencies ? '✅' : '❌'}`);
        
        // Take screenshot of the dropdown
        await page.screenshot({ 
          path: '/mnt/raid1/GitHub/allowance/tests/test-results/currency-dropdown-open.png', 
          fullPage: true 
        });
        
        // Test specific currencies that should be available from LNBits core
        const expectedCurrencies = ['USD', 'EUR', 'GBP', 'JPY', 'CAD', 'AUD', 'CHF', 'CNY'];
        const foundCurrencies = [];
        const missingCurrencies = [];
        
        for (const currency of expectedCurrencies) {
          const found = dropdownOptions.some(opt => opt.includes(currency));
          if (found) {
            foundCurrencies.push(currency);
          } else {
            missingCurrencies.push(currency);
          }
        }
        
        console.log(`✅ Found currencies: ${foundCurrencies.join(', ')}`);
        console.log(`❌ Missing currencies: ${missingCurrencies.join(', ')}`);
        
        // Close dropdown
        await page.keyboard.press('Escape');
        await page.waitForTimeout(500);
        
        // Step 7: Test selecting a currency and verify exchange rate fetch
        if (foundCurrencies.length > 0) {
          console.log('📝 Step 7: Testing currency selection and rate fetch...');
          
          const testCurrency = foundCurrencies[0];
          console.log(`🧪 Testing with currency: ${testCurrency}`);
          
          // Open dropdown again
          await currencySelect.click();
          await page.waitForTimeout(1000);
          
          // Select the test currency
          await page.click(`.q-item:has-text("${testCurrency}")`);
          await page.waitForTimeout(2000);
          
          // Check if exchange rate was fetched
          const rateInfo = await page.evaluate((currency) => {
            try {
              if (window.app && window.app.fiatRates) {
                return {
                  success: true,
                  rate: window.app.fiatRates[currency],
                  allRates: window.app.fiatRates
                };
              }
              return { success: false, error: 'Vue app or fiatRates not found' };
            } catch (error) {
              return { success: false, error: error.message };
            }
          }, testCurrency);
          
          console.log(`💱 Exchange rate info for ${testCurrency}:`, JSON.stringify(rateInfo, null, 2));
          
          // Check if the hint shows the exchange rate
          const amountInput = page.locator('input[type="number"]');
          await amountInput.fill('100');
          await page.waitForTimeout(1000);
          
          const hint = await page.locator('.q-field__bottom').textContent();
          console.log('💰 Amount field hint:', hint);
          
          const hasExchangeRateHint = hint && hint.includes('sats');
          console.log(`🔄 Exchange rate hint displayed: ${hasExchangeRateHint ? '✅' : '❌'}`);
        }
        
        // Final assessment
        console.log('\n🎯 CURRENCY DROPDOWN TEST RESULTS:');
        console.log('='.repeat(50));
        
        if (hasExtendedCurrencies) {
          console.log('✅ SUCCESS! Currency dropdown shows extended currency list');
          console.log(`   Found ${optionCount} currency options`);
          console.log(`   Available currencies: ${dropdownOptions.join(', ')}`);
          
          // Take success screenshot
          await page.screenshot({ 
            path: '/mnt/raid1/GitHub/allowance/tests/test-results/currency-test-success.png', 
            fullPage: true 
          });
          
          // Close form and exit successfully
          await page.keyboard.press('Escape');
          console.log('🎉 CURRENCY DROPDOWN TEST PASSED! 🎉');
          process.exit(0);
          
        } else {
          console.log('❌ FAILURE! Currency dropdown only shows basic currencies');
          console.log(`   Only found ${optionCount} currency options: ${dropdownOptions.join(', ')}`);
          console.log('   Expected: Full list of currencies from LNBits core API');
          
          // Take failure screenshot
          await page.screenshot({ 
            path: '/mnt/raid1/GitHub/allowance/tests/test-results/currency-test-failure.png', 
            fullPage: true 
          });
          
          // Close form
          await page.keyboard.press('Escape');
          console.log('💥 CURRENCY DROPDOWN TEST FAILED! 💥');
          process.exit(1);
        }
        
      } else {
        console.log('❌ Currency dropdown not found');
        await page.screenshot({ 
          path: '/mnt/raid1/GitHub/allowance/tests/test-results/currency-dropdown-not-found.png', 
          fullPage: true 
        });
        process.exit(1);
      }
      
    } else {
      console.log('❌ New Allowance button not found');
      await page.screenshot({ 
        path: '/mnt/raid1/GitHub/allowance/tests/test-results/new-allowance-button-not-found.png', 
        fullPage: true 
      });
      process.exit(1);
    }
    
  } catch (error) {
    console.error('💥 Error:', error.message);
    await page.screenshot({ 
      path: '/mnt/raid1/GitHub/allowance/tests/test-results/currency-test-error.png', 
      fullPage: true 
    });
    process.exit(1);
  } finally {
    await browser.close();
  }
})();