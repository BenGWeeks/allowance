const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

// Get test data from JSON file
const getTestData = () => {
  // Try to load from create-allowance.json
  const testDataPath = path.join(__dirname, 'create-allowance.json');
  if (fs.existsSync(testDataPath)) {
    const allowances = JSON.parse(fs.readFileSync(testDataPath, 'utf8'));
    if (Array.isArray(allowances) && allowances.length > 0) {
      return allowances;
    }
  }
  
  // Fallback to single default allowance
  return [{
    name: 'Pocket money',
    lightningAddress: 'muddledsmell08@walletofsatoshi.com',
    amount: 100,
    frequency: 'weekly',
    memo: 'Default test allowance'
  }];
};

(async () => {
  const allowancesToCreate = getTestData();
  console.log(`🎯 Testing ${allowancesToCreate.length} allowance(s) from create-allowance.json`);
  
  const browser = await chromium.launch({ headless: true, slowMo: 500 });
  const page = await browser.newPage();
  
  let successCount = 0;
  let failureCount = 0;

  try {
    console.log('🚀 Starting create allowance test...');
    
    // Listen for console errors
    page.on('console', msg => {
      if (msg.type() === 'error') {
        console.log('❌ Browser console error:', msg.text());
      }
    });
    
    page.on('pageerror', error => {
      console.log('💥 Page error:', error.message);
    });
    
    // Monitor network requests
    page.on('request', request => {
      if (request.url().includes('/allowance/api/v1/allowance') && request.method() === 'POST') {
        console.log('📤 POST request to create allowance:', request.url());
      }
    });
    
    let lastCreateResponse = null;
    page.on('response', response => {
      if (response.url().includes('/allowance/api/v1/allowance') && response.request().method() === 'POST') {
        lastCreateResponse = { status: response.status(), url: response.url() };
        console.log(`📥 POST response: ${response.status()} ${response.url()}`);
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
    
    // Step 3: Create allowances from JSON file
    for (let i = 0; i < allowancesToCreate.length; i++) {
      const testData = allowancesToCreate[i];
      lastCreateResponse = null; // Reset for this iteration
      console.log(`\n📝 Step 3.${i+1}: Creating allowance "${testData.name}" (${testData.amount} sats ${testData.frequency})...`);
    const newAllowanceButton = page.locator('button:has-text("New Allowance")');
    
    if (await newAllowanceButton.isVisible()) {
      await newAllowanceButton.click();
      await page.waitForTimeout(2000);
      
      // Fill the form
      console.log('📝 Filling allowance form...');
      
      // Wait for form inputs to appear
      await page.waitForSelector('input', { timeout: 10000 });
      
      // Check which inputs are visible and fillable
      const visibleInputs = await page.evaluate(() => {
        const inputs = Array.from(document.querySelectorAll('input'));
        return inputs.map((input, i) => ({
          index: i,
          type: input.type,
          placeholder: input.placeholder,
          visible: input.offsetParent !== null,
          disabled: input.disabled
        }));
      });
      console.log('📝 Input analysis:', JSON.stringify(visibleInputs, null, 2));
      
      // Fill only visible, enabled inputs
      const fillableInputs = visibleInputs.filter(input => input.visible && !input.disabled);
      console.log('📝 Fillable inputs:', fillableInputs.length);
      
      // Check for Vue mounted instance
      const vueDebug = await page.evaluate(() => {
        const debug = {};
        
        // Check if Vue app is mounted
        const vueEl = document.querySelector('#vue');
        if (vueEl && vueEl.__vue_app__) {
          debug.vueElFound = true;
          debug.vueApp = true;
          
          // Try to get the component instance
          const instance = vueEl.__vue_app__._instance;
          if (instance && instance.proxy) {
            debug.instanceFound = true;
            debug.instanceKeys = Object.keys(instance.proxy);
            if (instance.proxy.formDialog) {
              debug.formDialogFound = true;
              debug.formDialogData = instance.proxy.formDialog.data;
            }
          }
        }
        
        // Also check global window properties for Vue instances
        debug.windowKeys = Object.keys(window).filter(k => k.includes('vue') || k.includes('Vue'));
        
        return debug;
      });
      console.log('🔍 Vue instance debug:', JSON.stringify(vueDebug, null, 2));
      
      // Fill form fields using DOM manipulation with test data
      await page.fill('input[placeholder*="Weekly allowance"]', testData.name);
      console.log(`✅ Filled description field: ${testData.name}`);
      
      await page.fill('input[placeholder*="alice@getalby.com"]', testData.lightningAddress);
      console.log(`✅ Filled lightning address field: ${testData.lightningAddress}`);
      
      await page.fill('input[type="number"]', testData.amount.toString());
      console.log(`✅ Filled amount field: ${testData.amount}`);
      
      // Handle frequency dropdown - use the specific frequency select
      const frequencySelect = page.locator('.q-select').filter({ hasText: 'Frequency' });
      await frequencySelect.click();
      
      // Capitalize first letter for UI matching
      const frequencyLabel = testData.frequency.charAt(0).toUpperCase() + testData.frequency.slice(1);
      await page.waitForSelector(`.q-item:has-text("${frequencyLabel}")`);
      await page.click(`.q-item:has-text("${frequencyLabel}")`);
      console.log(`✅ Selected frequency: ${frequencyLabel}`);
      
      await page.waitForTimeout(1000); // Let Vue update
      
      // Take screenshot of filled form
      await page.screenshot({ path: '/mnt/raid1/GitHub/allowance/tests/test-results/form-filled.png', fullPage: true });
      console.log('📸 Form screenshot saved');
      
      // Check what Vue globals are available
      const vueGlobals = await page.evaluate(() => {
        const globals = {};
        if (typeof window.app !== 'undefined') globals.app = 'found';
        if (typeof window.Vue !== 'undefined') globals.Vue = 'found';
        if (typeof window.windowMixin !== 'undefined') globals.windowMixin = 'found';
        return globals;
      });
      console.log('🔍 Available Vue globals:', vueGlobals);
      
      // Check Vue form data after setting
      const vueFormData = await page.evaluate(() => {
        // Try different ways to access the Vue app
        if (window.app && window.app.formDialog) {
          return JSON.stringify(window.app.formDialog.data, null, 2);
        }
        return 'Vue app not accessible';
      });
      console.log('📊 Vue form data after setting:', vueFormData);
      
      // Wait a moment for Vue reactivity
      await page.waitForTimeout(1000);
      
      // Submit the form
      console.log('🖱️ Submitting form...');
      
      // Try multiple ways to submit the form
      console.log('🎯 Attempting form submission...');
      
      // Method 1: Trigger form submit event
      await page.evaluate(() => {
        const form = document.querySelector('form');
        if (form) {
          console.log('Found form, triggering submit event');
          form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
        }
      });
      
      await page.waitForTimeout(1000);
      
      // Method 2: Click submit button
      try {
        const submitButton = page.locator('button[type="submit"]:has-text("Create")');
        await submitButton.click({ timeout: 5000 });
        console.log('✅ Clicked submit button');
      } catch (error) {
        console.log('⚠️ Submit button click timeout - form may have already submitted');
      }
      
      // Wait for response - check if we got a successful POST response
      await page.waitForTimeout(5000);
      
      // Check if form dialog closed (success indicator)
      const dialogStillOpen = await page.locator('.q-dialog').isVisible();
      if (!dialogStillOpen) {
        console.log('🎉 Form dialog closed - likely successful submission!');
      }
      
      // Check if there are any validation error messages
      const errorMessages = await page.locator('.q-field--error, .q-form--error, .text-negative, .q-field-bottom .q-field__messages').allTextContents();
      if (errorMessages.length > 0) {
        console.log('🚨 Validation errors found:', errorMessages);
      }
      
      // Check console for any Vue/JavaScript errors
      const consoleErrors = await page.evaluate(() => {
        // Return any errors that might have occurred
        return window.lastError || 'No errors captured';
      });
      console.log('🐛 Console errors:', consoleErrors);
      
      // Check if the start date field has a value (it's required) - only if form still open
      try {
        const startDateValue = await page.inputValue('input[type="date"]', { timeout: 5000 });
        console.log('📅 Start date value:', startDateValue);
      } catch (error) {
        console.log('📅 Could not read start date - form may have closed');
      }
      
      // Check all form field values to see what's missing
      const formValues = await page.evaluate(() => {
        const inputs = document.querySelectorAll('input, select');
        const values = {};
        inputs.forEach((input, i) => {
          if (input.type !== 'checkbox') {
            values[`${input.type}_${i}`] = input.value;
          }
        });
        return values;
      });
      console.log('📋 Current form values:', formValues);
      
      // Check if loading state is still active (only if form still exists)
      try {
        const loadingButton = page.locator('button[type="submit"]');
        const isLoading = await loadingButton.getAttribute('loading', { timeout: 3000 });
        if (isLoading) {
          console.log('⏳ Form still loading...');
          await page.waitForTimeout(3000);
        }
      } catch (error) {
        console.log('⚠️ Submit button no longer available - form likely closed');
      }
      
      // Check if allowance was created successfully by looking at the table
      console.log('🔍 Checking for allowance in table...');
      
      // Wait for table to update
      await page.waitForTimeout(2000);
      
      // Check if we got an error response during creation (anything other than 200/201)
      if (lastCreateResponse && (lastCreateResponse.status < 200 || lastCreateResponse.status >= 300)) {
        console.log(`❌ CREATION FAILED: Server returned ${lastCreateResponse.status} error`);
        console.log(`   Reason: HTTP error prevented allowance creation`);
        failureCount++;
        await page.screenshot({ path: `/mnt/raid1/GitHub/allowance/tests/test-results/create-allowance-${i+1}-http-error.png`, fullPage: true });
        // Reset for next iteration
        lastCreateResponse = null;
        continue; // Skip to next allowance
      }
      
      const allowanceRows = page.locator(`tr:has-text("${testData.name}")`);
      const allowanceCount = await allowanceRows.count();
      
      if (allowanceCount > 0) {
        console.log(`✅ SUCCESS! Found ${allowanceCount} allowance(s) with "${testData.name}" in table!`);
        
        // Verify details from the first row - use more specific selectors to avoid conflicts
        const firstRow = allowanceRows.first();
        const rowText = await firstRow.textContent();
        const hasAmount = rowText.includes(testData.amount.toString());
        const hasAddress = rowText.includes(testData.lightningAddress);
        const hasFrequency = rowText.includes(testData.frequency);
        
        console.log(`  ✓ Amount: ${testData.amount} sats`, hasAmount ? '✅' : '❌');
        console.log(`  ✓ Address: ${testData.lightningAddress}`, hasAddress ? '✅' : '❌');
        console.log(`  ✓ Frequency: ${testData.frequency}`, hasFrequency ? '✅' : '❌');
        
        await page.screenshot({ path: `/mnt/raid1/GitHub/allowance/tests/test-results/create-allowance-${i+1}-success.png`, fullPage: true });
        console.log(`✅ Allowance "${testData.name}" created successfully!`);
        successCount++;
      } else {
        console.log(`❌ Allowance "${testData.name}" not found in table`);
        
        // Check if dialog is still open (error state)
        const dialogOpen = await page.locator('.q-dialog').isVisible();
        if (dialogOpen) {
          console.log('⚠️ Form dialog still open - possible validation error');
          await page.screenshot({ path: `/mnt/raid1/GitHub/allowance/tests/test-results/create-allowance-${i+1}-validation-error.png`, fullPage: true });
        }
        failureCount++;
      }
      
    } else {
      console.log(`❌ New Allowance button not found for "${testData.name}"`);
      await page.screenshot({ path: `/mnt/raid1/GitHub/allowance/tests/test-results/create-allowance-${i+1}-no-button.png`, fullPage: true });
      failureCount++;
    }
    
    // Wait a bit between allowances
    if (i < allowancesToCreate.length - 1) {
      await page.waitForTimeout(2000);
    }
  } // End of for loop
  
  // Final results
  console.log(`\n🎯 FINAL RESULTS:`);
  console.log(`✅ Successful: ${successCount}/${allowancesToCreate.length}`);
  console.log(`❌ Failed: ${failureCount}/${allowancesToCreate.length}`);
  
  if (successCount === allowancesToCreate.length) {
    console.log('🎉 ALL ALLOWANCE CREATION TESTS PASSED! 🎉');
    await page.screenshot({ path: 'tests/test-results/create-allowance-all-success.png', fullPage: true });
  } else {
    console.log('💥 SOME ALLOWANCE CREATION TESTS FAILED!');
    await page.screenshot({ path: 'tests/test-results/create-allowance-final-state.png', fullPage: true });
  }
    
  } catch (error) {
    console.error('💥 Error:', error.message);
    await page.screenshot({ path: 'tests/test-results/create-allowance-error.png', fullPage: true });
    failureCount = allowancesToCreate.length; // Mark all as failed
  } finally {
    await browser.close();
  }
  
  // Exit with appropriate code
  process.exit(failureCount === 0 ? 0 : 1);
})();