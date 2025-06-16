const { chromium } = require('playwright');
const helpers = require('./test-helpers');

// Get test data from command line args or default values
const getTestData = () => {
  const args = process.argv.slice(2);
  if (args.length >= 4) {
    return {
      name: args[0],
      lightningAddress: args[1], 
      amount: parseInt(args[2]),
      frequency: args[3]
    };
  }
  
  // Default test data with timestamp to avoid duplicates
  const timestamp = Date.now();
  return {
    name: `Test Allowance ${timestamp}`,
    lightningAddress: 'muddledsmell08@walletofsatoshi.com',
    amount: 50,
    frequency: 'weekly'
  };
};

(async () => {
  const testData = getTestData();
  console.log(`🎯 Testing allowance creation: ${testData.name} (${testData.amount} sats ${testData.frequency})`);
  
  const browser = await chromium.launch({ headless: true, slowMo: 500 });
  const page = await browser.newPage();

  try {
    console.log('🚀 Starting create allowance test...');
    
    // Step 1: Login and navigate
    await helpers.loginAsAdmin(page);
    await helpers.navigateToAllowance(page);
    
    // Step 2: Get initial count
    const initialCount = await helpers.getAllowanceCount(page);
    console.log(`📊 Initial allowance count: ${initialCount}`);
    
    // Step 3: Open create dialog
    console.log('📝 Opening create allowance dialog...');
    const newButton = page.locator('button:has-text("New Allowance")');
    await newButton.click();
    await page.waitForTimeout(2000);
    
    // Step 4: Fill form
    console.log('📝 Filling allowance form...');
    await page.fill('input[placeholder*="Weekly allowance"]', testData.name);
    await page.fill('input[placeholder*="alice@getalby.com"]', testData.lightningAddress);
    await page.fill('input[type="number"]', testData.amount.toString());
    
    // Handle frequency dropdown
    const frequencySelect = page.locator('.q-select').filter({ hasText: 'Frequency' });
    await frequencySelect.click();
    const frequencyLabel = testData.frequency.charAt(0).toUpperCase() + testData.frequency.slice(1);
    await page.click(`.q-item:has-text("${frequencyLabel}")`);
    
    // Fill start date (required field) - set to today
    const today = new Date().toISOString().split('T')[0];
    const startDateInput = page.locator('input[aria-label*="Start Date"]');
    if (await startDateInput.isVisible()) {
      await startDateInput.fill(today);
      console.log(`✅ Filled start date: ${today}`);
    }
    
    // Skip currency selection for now - it may be optional
    
    await page.waitForTimeout(1000);
    
    // Step 5: Submit form through UI
    console.log('🖱️ Submitting form...');
    const submitButton = page.locator('button[type="submit"]:has-text("Create")');
    await submitButton.click();
    
    // Wait for dialog to close (indicates submission)
    await page.waitForTimeout(3000);
    
    // Check if dialog is still open
    const dialogStillOpen = await page.locator('.q-dialog').isVisible();
    if (dialogStillOpen) {
      console.log('⚠️ Dialog still open after submit - checking for errors');
      
      // Look for error messages
      const errorTexts = await page.locator('.q-field__messages, .text-negative').allTextContents();
      if (errorTexts.length > 0) {
        console.log('❌ Form validation errors:', errorTexts);
      }
      
      // Check form field values
      const formData = await page.evaluate(() => {
        const inputs = document.querySelectorAll('input, select');
        const data = {};
        inputs.forEach((input) => {
          if (input.name || input.placeholder) {
            data[input.name || input.placeholder] = input.value;
          }
        });
        return data;
      });
      console.log('📋 Form data:', formData);
    }
    
    // Step 6: Verify creation succeeded by checking count via API
    console.log('⏳ Verifying allowance was created...');
    const countChanged = await helpers.waitForCountChange(page, 1, initialCount, 10000);
    
    if (countChanged) {
      // Step 7: Verify the allowance exists in API and check details
      const createdAllowance = await helpers.findAllowanceByName(page, testData.name);
      
      if (createdAllowance) {
        console.log('✅ Allowance found in API:', {
          id: createdAllowance.id,
          name: createdAllowance.name,
          amount: createdAllowance.amount,
          lightning_address: createdAllowance.lightning_address,
          frequency_type: createdAllowance.frequency_type
        });
        
        // Verify details match what was entered in UI
        const detailsMatch = 
          createdAllowance.name === testData.name &&
          createdAllowance.amount === testData.amount &&
          createdAllowance.lightning_address === testData.lightningAddress &&
          createdAllowance.frequency_type === testData.frequency;
        
        if (detailsMatch) {
          // Also verify it appears in the UI table
          const rowInTable = await page.locator(`tr:has-text("${testData.name}")`).isVisible();
          if (rowInTable) {
            await page.screenshot({ path: '/mnt/raid1/GitHub/allowance/tests/test-results/create-allowance-success.png', fullPage: true });
            console.log('✅ Allowance visible in UI table');
            console.log('🎉 ALLOWANCE CREATION TEST PASSED! 🎉');
            process.exit(0);
          } else {
            console.log('❌ Allowance created but not visible in UI table');
            process.exit(1);
          }
        } else {
          console.log('❌ Allowance details do not match expected values');
          console.log('Expected:', testData);
          console.log('Actual:', {
            name: createdAllowance.name,
            amount: createdAllowance.amount,
            lightning_address: createdAllowance.lightning_address,
            frequency_type: createdAllowance.frequency_type
          });
          process.exit(1);
        }
      } else {
        console.log('❌ Allowance not found in API after creation');
        process.exit(1);
      }
    } else {
      console.log('❌ Allowance count did not increase - UI creation failed');
      
      // Check if dialog is still open (indicates validation error)
      const dialogOpen = await page.locator('.q-dialog').isVisible();
      if (dialogOpen) {
        console.log('⚠️ Create dialog still open - possible validation error');
      }
      
      await page.screenshot({ path: '/mnt/raid1/GitHub/allowance/tests/test-results/create-allowance-failed.png', fullPage: true });
      process.exit(1);
    }
    
  } catch (error) {
    console.error('💥 Error:', error.message);
    await page.screenshot({ path: '/mnt/raid1/GitHub/allowance/tests/test-results/create-allowance-error.png', fullPage: true });
    process.exit(1);
  } finally {
    await browser.close();
  }
})();