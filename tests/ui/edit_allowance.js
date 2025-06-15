const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

// Get test data from command line args or default values
const getTestData = () => {
  // Check command line arguments
  const args = process.argv.slice(2);
  if (args.length >= 2) {
    return {
      originalName: args[0],
      newName: args[1],
      newAmount: args[2] ? parseInt(args[2]) : null,
      newFrequency: args[3] || null
    };
  }
  
  // Default test data
  return {
    originalName: 'Daily Coffee Money',
    newName: 'Updated Coffee Budget',
    newAmount: 35,
    newFrequency: 'weekly'
  };
};

(async () => {
  const testData = getTestData();
  console.log(`🎯 Testing allowance edit: "${testData.originalName}" -> "${testData.newName}"`);
  
  const browser = await chromium.launch({ headless: true, slowMo: 500 });
  const page = await browser.newPage();

  try {
    console.log('🚀 Starting edit allowance test...');
    
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
      if (request.url().includes('/allowance/api/v1/allowance') && request.method() === 'PUT') {
        console.log('📤 PUT request to update allowance:', request.url());
      }
    });
    
    page.on('response', response => {
      if (response.url().includes('/allowance/api/v1/allowance') && response.request().method() === 'PUT') {
        console.log(`📥 PUT response: ${response.status()} ${response.url()}`);
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
    
    // Step 3: Find and edit existing allowance
    console.log(`📝 Step 3: Finding allowance "${testData.originalName}" to edit...`);
    
    // Look for the allowance row (use first if multiple matches)
    const allowanceRow = page.locator(`tr:has-text("${testData.originalName}")`).first();
    const rowExists = await allowanceRow.isVisible();
    
    if (!rowExists) {
      console.log(`❌ Allowance "${testData.originalName}" not found in table`);
      await page.screenshot({ path: '/mnt/raid1/GitHub/allowance/tests/test-results/edit-allowance-not-found.png', fullPage: true });
      process.exit(1);
    }
    
    console.log(`✅ Found allowance "${testData.originalName}"`);
    
    // Click the edit button for this allowance (look for light-blue colored button which is edit)
    const editButton = allowanceRow.locator('button.text-light-blue, button[color="light-blue"]');
    await editButton.click();
    console.log('🖱️ Clicked edit button');
    
    await page.waitForTimeout(2000);
    
    // Step 4: Update the allowance form
    console.log('📝 Step 4: Updating allowance form...');
    
    // Wait for form to appear
    await page.waitForSelector('input', { timeout: 10000 });
    
    // Update description field
    await page.fill('input[placeholder*="Weekly allowance"]', testData.newName);
    console.log(`✅ Updated description: ${testData.newName}`);
    
    // Update amount if provided
    if (testData.newAmount) {
      await page.fill('input[type="number"]', testData.newAmount.toString());
      console.log(`✅ Updated amount: ${testData.newAmount}`);
    }
    
    // Update frequency if provided
    if (testData.newFrequency) {
      const frequencySelect = page.locator('.q-select').filter({ hasText: 'Frequency' });
      await frequencySelect.click();
      
      const frequencyLabel = testData.newFrequency.charAt(0).toUpperCase() + testData.newFrequency.slice(1);
      await page.waitForSelector(`.q-item:has-text("${frequencyLabel}")`);
      await page.click(`.q-item:has-text("${frequencyLabel}")`);
      console.log(`✅ Updated frequency: ${frequencyLabel}`);
    }
    
    await page.waitForTimeout(1000);
    
    // Take screenshot of updated form
    await page.screenshot({ path: '/mnt/raid1/GitHub/allowance/tests/test-results/edit-allowance-form.png', fullPage: true });
    console.log('📸 Form screenshot saved');
    
    // Step 5: Submit the form
    console.log('🖱️ Submitting updated form...');
    
    // Capture the allowance ID for API verification
    const allowanceId = await page.locator('.q-table tbody tr').first().locator('td').first().textContent();
    console.log(`📋 Allowance ID for verification: ${allowanceId}`);

    // Capture API key from network requests
    let apiKey = null;
    page.on('request', request => {
      if (request.url().includes('/allowance/api/v1/allowance') && request.headers()['x-api-key']) {
        apiKey = request.headers()['x-api-key'];
      }
    });

    // Get initial state via API before making changes
    let initialState = null;
    
    // Wait for API key to be captured during page load
    await page.waitForTimeout(2000);
    
    if (apiKey) {
      console.log('🔍 Getting initial allowance state from API...');
      try {
        const initialResponse = await page.request.get(`http://localhost:5001/allowance/api/v1/allowance/${allowanceId}`, {
          headers: { 'X-API-Key': apiKey }
        });
        
        if (initialResponse.ok()) {
          initialState = await initialResponse.json();
          console.log('📊 Initial state from API:');
          console.log(`  Name: ${initialState.name}`);
          console.log(`  Amount: ${initialState.amount}`);
          console.log(`  Active: ${initialState.active} (type: ${typeof initialState.active})`);
          console.log(`  Frequency: ${initialState.frequency_type}`);
        }
      } catch (error) {
        console.log('⚠️ Could not get initial state:', error.message);
      }
    }
    
    // Monitor network requests
    const networkResponses = [];
    page.on('response', response => {
      if (response.url().includes('/allowance/api/v1/allowance') && response.request().method() === 'PUT') {
        networkResponses.push({
          status: response.status(),
          url: response.url(),
          method: response.request().method()
        });
        console.log(`🌐 PUT request: ${response.status()} ${response.url()}`);
      }
    });
    
    // Check active toggle state before submission using correct selector
    await page.waitForTimeout(1000);
    const toggleElement = page.locator('.q-toggle');
    const isToggleActive = await toggleElement.getAttribute('aria-checked') === 'true' || 
                          await toggleElement.locator('.q-toggle__thumb--true').isVisible().catch(() => false);
    
    // Also check the Vue debug display
    const debugText = await page.locator('.text-caption').textContent().catch(() => 'No debug text');
    
    console.log(`🔘 Active toggle state before submit: ${isToggleActive ? 'ON' : 'OFF'}`);
    console.log(`📊 Vue debug display: ${debugText}`);
    
    try {
      // Try different button selectors
      const submitButtons = [
        'button[type="submit"]:has-text("Update")',
        'button:has-text("UPDATE ALLOWANCE")',
        '.q-btn:has-text("UPDATE")',
        '.q-btn:has-text("Update")'
      ];
      
      let buttonClicked = false;
      for (const selector of submitButtons) {
        const button = page.locator(selector);
        if (await button.isVisible()) {
          console.log(`🔍 Found submit button: ${selector}`);
          await button.click();
          buttonClicked = true;
          break;
        }
      }
      
      if (buttonClicked) {
        console.log('✅ Clicked update button');
      } else {
        console.log('❌ No submit button found');
        // List all buttons
        const allButtons = await page.locator('button').all();
        console.log(`🔍 Available buttons: ${allButtons.length}`);
        for (let i = 0; i < allButtons.length; i++) {
          const text = await allButtons[i].textContent();
          console.log(`  Button ${i}: "${text}"`);
        }
      }
    } catch (error) {
      console.log('⚠️ Update button click error:', error.message);
    }
    
    // Wait for response
    await page.waitForTimeout(5000);
    
    // Check network responses
    if (networkResponses.length > 0) {
      console.log(`📡 Network responses: ${networkResponses.length}`);
      networkResponses.forEach(res => {
        console.log(`  ${res.method} ${res.status} ${res.url}`);
      });
    } else {
      console.log('⚠️ No PUT requests detected - form may not have submitted');
    }
    
    // Check if form dialog closed (success indicator)
    const dialogStillOpen = await page.locator('.q-dialog').isVisible();
    if (!dialogStillOpen) {
      console.log('🎉 Form dialog closed - likely successful update!');
    }
    
    // Step 6: Verify the update in the table
    console.log('🔍 Checking for updated allowance in table...');
    
    // Wait for table to update
    await page.waitForTimeout(2000);
    
    const updatedRow = page.locator(`tr:has-text("${testData.newName}")`);
    const updatedExists = await updatedRow.isVisible();
    
    if (updatedExists) {
      console.log(`✅ SUCCESS! Found updated allowance "${testData.newName}" in table!`);
      
      // Verify updated details
      const rowText = await updatedRow.first().textContent();
      const hasNewAmount = testData.newAmount ? rowText.includes(testData.newAmount.toString()) : true;
      const hasNewFrequency = testData.newFrequency ? rowText.includes(testData.newFrequency) : true;
      
      console.log(`  ✓ Updated name: ${testData.newName} ✅`);
      if (testData.newAmount) {
        console.log(`  ✓ Updated amount: ${testData.newAmount} sats`, hasNewAmount ? '✅' : '❌');
      }
      if (testData.newFrequency) {
        console.log(`  ✓ Updated frequency: ${testData.newFrequency}`, hasNewFrequency ? '✅' : '❌');
      }
      
      // Step 7: Verify update via API
      if (apiKey && allowanceId) {
        console.log('\n🔍 Verifying update via API...');
        try {
          const verifyResponse = await page.request.get(`http://localhost:5001/allowance/api/v1/allowance/${allowanceId}`, {
            headers: { 'X-API-Key': apiKey }
          });
          
          if (verifyResponse.ok()) {
            const apiData = await verifyResponse.json();
            console.log('📊 API verification results:');
            console.log(`  Database ID: ${apiData.id}`);
            console.log(`  Database name: ${apiData.name}`);
            console.log(`  Database amount: ${apiData.amount}`);
            console.log(`  Database active: ${apiData.active} (type: ${typeof apiData.active})`);
            console.log(`  Database frequency: ${apiData.frequency_type}`);
            
            // Verify API data matches expectations
            const apiNameMatch = apiData.name === testData.newName;
            const apiAmountMatch = testData.newAmount ? apiData.amount.toString() === testData.newAmount.toString() : true;
            const apiActiveIsBoolean = typeof apiData.active === 'boolean';
            
            console.log('\n📋 API Verification:');
            console.log(`  ✓ Name in DB: ${apiNameMatch ? '✅' : '❌'} (${apiData.name})`);
            if (testData.newAmount) {
              console.log(`  ✓ Amount in DB: ${apiAmountMatch ? '✅' : '❌'} (${apiData.amount})`);
            }
            console.log(`  ✓ Active is boolean: ${apiActiveIsBoolean ? '✅' : '❌'}`);
            console.log(`  ✓ Active value: ${apiData.active}`);
            
            if (apiNameMatch && apiAmountMatch && apiActiveIsBoolean) {
              console.log('\n🎉 API VERIFICATION PASSED - Database updated correctly!');
            } else {
              console.log('\n⚠️ API VERIFICATION ISSUES - Check database state');
            }
          } else {
            console.log(`❌ API verification failed: ${verifyResponse.status()}`);
          }
        } catch (error) {
          console.log(`❌ API verification error: ${error.message}`);
        }
      } else {
        console.log('⚠️ API verification skipped - missing API key or allowance ID');
      }
      
      await page.screenshot({ path: '/mnt/raid1/GitHub/allowance/tests/test-results/edit-allowance-success.png', fullPage: true });
      console.log('\n🎉 ALLOWANCE EDIT TEST PASSED! 🎉');
      process.exit(0); // Success
    } else {
      console.log(`❌ Updated allowance "${testData.newName}" not found in table`);
      
      // API verification even in failure case to see what's actually in the database
      if (apiKey && allowanceId) {
        console.log('\n🔍 Checking database state via API (failure case)...');
        try {
          const verifyResponse = await page.request.get(`http://localhost:5001/allowance/api/v1/allowance/${allowanceId}`, {
            headers: { 'X-API-Key': apiKey }
          });
          
          if (verifyResponse.ok()) {
            const apiData = await verifyResponse.json();
            console.log('📊 Actual database state:');
            console.log(`  Database ID: ${apiData.id}`);
            console.log(`  Database name: ${apiData.name}`);
            console.log(`  Database amount: ${apiData.amount}`);
            console.log(`  Database active: ${apiData.active} (type: ${typeof apiData.active})`);
            console.log(`  Database frequency: ${apiData.frequency_type}`);
            
            // Check if database was updated despite UI showing failure
            const dbNameChanged = apiData.name !== testData.originalName;
            const dbAmountChanged = testData.newAmount ? apiData.amount.toString() === testData.newAmount.toString() : false;
            
            console.log('🔍 Comparing database changes:');
            console.log(`  Expected name change: ${testData.originalName} → ${testData.newName}`);
            console.log(`  Actual name in DB: ${apiData.name}`);
            console.log(`  Expected amount change: ${initialState ? initialState.amount : 'unknown'} → ${testData.newAmount}`);
            console.log(`  Actual amount in DB: ${apiData.amount}`);
            
            if (dbNameChanged || dbAmountChanged) {
              console.log('⚠️ Database WAS updated despite UI not reflecting changes!');
              console.log('   This indicates a UI refresh/display issue, not an API issue');
            } else {
              console.log('✅ Database correctly unchanged (update truly failed)');
            }
          }
        } catch (error) {
          console.log(`❌ API check error: ${error.message}`);
        }
      }
      
      // Check if dialog is still open (error state)
      const dialogOpen = await page.locator('.q-dialog').isVisible();
      if (dialogOpen) {
        console.log('⚠️ Form dialog still open - possible validation error');
        await page.screenshot({ path: '/mnt/raid1/GitHub/allowance/tests/test-results/edit-allowance-error.png', fullPage: true });
        process.exit(1); // Failure
      }
      
      // Check if original name still exists (update failed)
      const originalStillExists = await page.locator(`tr:has-text("${testData.originalName}")`).isVisible();
      if (originalStillExists) {
        console.log(`⚠️ Original allowance "${testData.originalName}" still exists - update may have failed`);
      }
    }
    
    // Final screenshot
    await page.screenshot({ path: '/mnt/raid1/GitHub/allowance/tests/test-results/edit-allowance-final.png', fullPage: true });
    process.exit(1); // Failure
    
  } catch (error) {
    console.error('💥 Error:', error.message);
    await page.screenshot({ path: '/mnt/raid1/GitHub/allowance/tests/test-results/edit-allowance-error.png', fullPage: true });
    process.exit(1); // Failure
  } finally {
    await browser.close();
  }
})();