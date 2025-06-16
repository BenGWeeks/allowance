const { chromium } = require('playwright');
const helpers = require('./test-helpers');

// Get test data from command line args or default values
const getTestData = () => {
  const args = process.argv.slice(2);
  if (args.length >= 2) {
    return {
      originalName: args[0],
      newName: args[1],
      newAmount: args[2] ? parseInt(args[2]) : null,
      newFrequency: args[3] || null
    };
  }
  
  // Default test data - will edit the first allowance found
  return {
    originalName: null, // Will be set to first allowance found
    newName: `Edited Allowance ${Date.now()}`,
    newAmount: 75,
    newFrequency: 'daily'
  };
};

(async () => {
  let testData = getTestData();
  console.log(`🎯 Testing allowance edit`);
  
  const browser = await chromium.launch({ headless: true, slowMo: 500 });
  const page = await browser.newPage();

  try {
    console.log('🚀 Starting edit allowance test...');
    
    // Step 1: Login and navigate
    await helpers.loginAsAdmin(page);
    await helpers.navigateToAllowance(page);
    
    // Step 2: Get initial count and find an allowance to edit
    const initialCount = await helpers.getAllowanceCount(page);
    console.log(`📊 Initial allowance count: ${initialCount}`);
    
    if (initialCount === 0) {
      console.log('❌ No allowances found to edit');
      process.exit(1);
    }
    
    // Find allowance to edit
    const allowances = await helpers.getAllowances(page);
    let targetAllowance;
    
    if (testData.originalName) {
      targetAllowance = allowances.find(a => a.name === testData.originalName);
      if (!targetAllowance) {
        console.log(`❌ Allowance "${testData.originalName}" not found`);
        process.exit(1);
      }
    } else {
      // Use the first allowance
      targetAllowance = allowances[0];
      testData.originalName = targetAllowance.name;
    }
    
    console.log(`📝 Editing allowance: "${targetAllowance.name}" (ID: ${targetAllowance.id})`);
    
    // Step 3: Click edit button for the target allowance
    console.log('📝 Opening edit dialog...');
    const editButton = page.locator(`tr:has-text("${targetAllowance.name}") button:has-text("Edit")`);
    await editButton.click();
    await page.waitForTimeout(2000);
    
    // Step 4: Update form fields
    console.log('📝 Updating form fields...');
    
    // Clear and fill name field
    const nameInput = page.locator('input[placeholder*="Weekly allowance"]');
    await nameInput.selectAll();
    await nameInput.fill(testData.newName);
    
    // Update amount if specified
    if (testData.newAmount) {
      const amountInput = page.locator('input[type="number"]');
      await amountInput.selectAll();
      await amountInput.fill(testData.newAmount.toString());
    }
    
    // Update frequency if specified
    if (testData.newFrequency) {
      const frequencySelect = page.locator('.q-select').filter({ hasText: 'Frequency' });
      await frequencySelect.click();
      const frequencyLabel = testData.newFrequency.charAt(0).toUpperCase() + testData.newFrequency.slice(1);
      await page.click(`.q-item:has-text("${frequencyLabel}")`);
    }
    
    await page.waitForTimeout(1000);
    
    // Step 5: Submit form through UI
    console.log('🖱️ Submitting update...');
    const updateButton = page.locator('button[type="submit"]:has-text("Update")');
    await updateButton.click();
    
    // Wait for dialog to close (indicates submission)
    await page.waitForTimeout(3000);
    
    // Step 6: Verify edit succeeded - count should stay the same
    console.log('⏳ Verifying allowance was updated...');
    const finalCount = await helpers.getAllowanceCount(page);
    
    if (finalCount !== initialCount) {
      console.log(`⚠️ Count changed unexpectedly: ${initialCount} -> ${finalCount}`);
    }
    
    // Step 7: Verify the changes via API using the original ID
    const updatedAllowance = await helpers.getAllowanceById(page, targetAllowance.id);
    
    if (updatedAllowance) {
      console.log('✅ Updated allowance found in API by ID:', {
        id: updatedAllowance.id,
        name: updatedAllowance.name,
        amount: updatedAllowance.amount,
        frequency_type: updatedAllowance.frequency_type
      });
      
      // Verify changes
      let changesCorrect = updatedAllowance.name === testData.newName;
      
      if (testData.newAmount) {
        changesCorrect = changesCorrect && updatedAllowance.amount === testData.newAmount;
      }
      
      if (testData.newFrequency) {
        changesCorrect = changesCorrect && updatedAllowance.frequency_type === testData.newFrequency;
      }
      
      if (changesCorrect) {
        // Also verify it appears in the UI table with new name
        const rowInTable = await page.locator(`tr:has-text("${testData.newName}")`).isVisible();
        if (rowInTable) {
          await page.screenshot({ path: '/mnt/raid1/GitHub/allowance/tests/test-results/edit-allowance-success.png', fullPage: true });
          console.log('✅ Updated allowance visible in UI table');
          console.log('🎉 ALLOWANCE EDIT TEST PASSED! 🎉');
          process.exit(0);
        } else {
          console.log('❌ Allowance updated in API but not visible in UI table');
          process.exit(1);
        }
      } else {
        console.log('❌ Allowance updates do not match expected values');
        console.log('Expected changes:', {
          name: testData.newName,
          amount: testData.newAmount,
          frequency: testData.newFrequency
        });
        console.log('Actual values:', {
          name: updatedAllowance.name,
          amount: updatedAllowance.amount,
          frequency: updatedAllowance.frequency_type
        });
        process.exit(1);
      }
    } else {
      console.log('❌ Allowance with ID not found in API after edit');
      console.log(`  Looked for ID: ${targetAllowance.id}`);
      
      // Double-check by searching for new name
      const allowanceByNewName = await helpers.findAllowanceByName(page, testData.newName);
      if (allowanceByNewName) {
        console.log('⚠️ Found allowance by new name but with different ID - possible recreation instead of edit');
      }
      
      process.exit(1);
    }
    
  } catch (error) {
    console.error('💥 Error:', error.message);
    await page.screenshot({ path: '/mnt/raid1/GitHub/allowance/tests/test-results/edit-allowance-error.png', fullPage: true });
    process.exit(1);
  } finally {
    await browser.close();
  }
})();