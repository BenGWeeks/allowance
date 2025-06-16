const { chromium } = require('playwright');
const helpers = require('./test-helpers');

// Get test data from command line args or default values
const getTestData = () => {
  const args = process.argv.slice(2);
  if (args.length >= 1) {
    return {
      nameToDelete: args[0]
    };
  }
  
  // Default - will delete the first allowance found
  return {
    nameToDelete: null
  };
};

(async () => {
  let testData = getTestData();
  console.log(`🎯 Testing allowance deletion`);
  
  const browser = await chromium.launch({ headless: true, slowMo: 500 });
  const page = await browser.newPage();

  try {
    console.log('🚀 Starting delete allowance test...');
    
    // Step 1: Login and navigate
    await helpers.loginAsAdmin(page);
    await helpers.navigateToAllowance(page);
    
    // Step 2: Get initial count and find an allowance to delete
    const initialCount = await helpers.getAllowanceCount(page);
    console.log(`📊 Initial allowance count: ${initialCount}`);
    
    if (initialCount === 0) {
      console.log('❌ No allowances found to delete');
      process.exit(1);
    }
    
    // Find allowance to delete
    const allowances = await helpers.getAllowances(page);
    let targetAllowance;
    
    if (testData.nameToDelete) {
      targetAllowance = allowances.find(a => a.name === testData.nameToDelete);
      if (!targetAllowance) {
        console.log(`❌ Allowance "${testData.nameToDelete}" not found`);
        process.exit(1);
      }
    } else {
      // Use the first allowance
      targetAllowance = allowances[0];
      testData.nameToDelete = targetAllowance.name;
    }
    
    console.log(`🗑️ Deleting allowance: "${targetAllowance.name}" (ID: ${targetAllowance.id})`);
    
    // Step 3: Click delete button for the target allowance
    console.log('📝 Clicking delete button...');
    const deleteButton = page.locator(`tr:has-text("${targetAllowance.name}") button:has-text("Delete")`);
    await deleteButton.click();
    
    // Step 4: Confirm deletion in dialog
    console.log('📝 Confirming deletion...');
    await page.waitForTimeout(1000); // Wait for confirmation dialog
    
    // Look for confirmation button (could be "Delete", "Confirm", "Yes", etc.)
    const confirmButtons = [
      'button:has-text("Delete")',
      'button:has-text("Confirm")', 
      'button:has-text("Yes")',
      'button:has-text("OK")'
    ];
    
    let confirmed = false;
    for (const selector of confirmButtons) {
      try {
        const confirmButton = page.locator(selector);
        if (await confirmButton.isVisible({ timeout: 2000 })) {
          await confirmButton.click();
          confirmed = true;
          console.log(`✅ Clicked confirmation button: ${selector}`);
          break;
        }
      } catch (e) {
        // Button not found, try next one
      }
    }
    
    if (!confirmed) {
      console.log('⚠️ No confirmation dialog found - deletion may be immediate');
    }
    
    // Step 5: Wait for deletion to complete via UI, then verify count change
    console.log('⏳ Waiting for allowance to be deleted...');
    const countChanged = await helpers.waitForCountChange(page, -1, initialCount, 10000);
    
    if (countChanged) {
      // Step 6: Verify the allowance no longer exists in API by ID
      const deletedAllowance = await helpers.getAllowanceById(page, targetAllowance.id);
      
      if (!deletedAllowance) {
        // Also verify it's not visible in the UI table
        const rowInTable = await page.locator(`tr:has-text("${targetAllowance.name}")`).isVisible();
        if (!rowInTable) {
          await page.screenshot({ path: '/mnt/raid1/GitHub/allowance/tests/test-results/delete-allowance-success.png', fullPage: true });
          console.log('✅ Allowance not visible in UI table');
          console.log('🎉 ALLOWANCE DELETION TEST PASSED! 🎉');
          console.log(`✅ Allowance "${targetAllowance.name}" (ID: ${targetAllowance.id}) successfully deleted`);
          process.exit(0);
        } else {
          console.log('❌ Allowance deleted from API but still visible in UI table');
          process.exit(1);
        }
      } else {
        console.log('❌ Allowance still exists in API after deletion');
        console.log('Remaining allowance:', deletedAllowance);
        process.exit(1);
      }
    } else {
      console.log('❌ Allowance count did not decrease - UI deletion failed');
      
      // Check if allowance still exists by ID
      const stillExists = await helpers.getAllowanceById(page, targetAllowance.id);
      if (stillExists) {
        console.log('⚠️ Allowance still exists in API');
      }
      
      await page.screenshot({ path: '/mnt/raid1/GitHub/allowance/tests/test-results/delete-allowance-failed.png', fullPage: true });
      process.exit(1);
    }
    
  } catch (error) {
    console.error('💥 Error:', error.message);
    await page.screenshot({ path: '/mnt/raid1/GitHub/allowance/tests/test-results/delete-allowance-error.png', fullPage: true });
    process.exit(1);
  } finally {
    await browser.close();
  }
})();