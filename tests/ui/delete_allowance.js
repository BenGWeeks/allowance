const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

// Get test data from command line args or default values
const getTestData = () => {
  // Check command line arguments
  const args = process.argv.slice(2);
  if (args.length >= 1) {
    return {
      nameToDelete: args[0]
    };
  }
  
  // Default test data
  return {
    nameToDelete: 'Daily Snacks'
  };
};

(async () => {
  const testData = getTestData();
  console.log(`🎯 Testing allowance deletion: "${testData.nameToDelete}"`);
  
  const browser = await chromium.launch({ headless: true, slowMo: 500 });
  const page = await browser.newPage();

  try {
    console.log('🚀 Starting delete allowance test...');
    
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
      if (request.url().includes('/allowance/api/v1/allowance') && request.method() === 'DELETE') {
        console.log('📤 DELETE request to remove allowance:', request.url());
      }
    });
    
    page.on('response', response => {
      if (response.url().includes('/allowance/api/v1/allowance') && response.request().method() === 'DELETE') {
        console.log(`📥 DELETE response: ${response.status()} ${response.url()}`);
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
    
    // Step 3: Count existing allowances before deletion
    console.log('📝 Step 3: Counting existing allowances...');
    const allRowsBefore = page.locator('tbody tr');
    const countBefore = await allRowsBefore.count();
    console.log(`📊 Found ${countBefore} allowances before deletion`);
    
    // Step 4: Find and delete the specified allowance
    console.log(`📝 Step 4: Finding allowance "${testData.nameToDelete}" to delete...`);
    
    // Look for the allowance row (use first if multiple matches)
    const allowanceRow = page.locator(`tr:has-text("${testData.nameToDelete}")`).first();
    const rowExists = await allowanceRow.isVisible();
    
    if (!rowExists) {
      console.log(`❌ Allowance "${testData.nameToDelete}" not found in table`);
      await page.screenshot({ path: '/mnt/raid1/GitHub/allowance/tests/test-results/delete-allowance-not-found.png', fullPage: true });
      process.exit(1);
    }
    
    console.log(`✅ Found allowance "${testData.nameToDelete}"`);
    
    // Take screenshot before deletion
    await page.screenshot({ path: '/mnt/raid1/GitHub/allowance/tests/test-results/delete-allowance-before.png', fullPage: true });
    
    // Click the delete button for this allowance (look for pink colored button which is delete)
    const deleteButton = allowanceRow.locator('button.text-pink, button[color="pink"]');
    await deleteButton.click();
    console.log('🖱️ Clicked delete button');
    
    await page.waitForTimeout(1000);
    
    // Step 5: Handle confirmation dialog
    console.log('📝 Step 5: Handling confirmation dialog...');
    
    // Wait for confirmation dialog to appear
    try {
      await page.waitForSelector('.q-dialog', { timeout: 5000 });
      console.log('✅ Confirmation dialog appeared');
      
      // Look for confirmation button (OK, Yes, Confirm, etc.)
      const confirmButtons = [
        'button:has-text("OK")',
        'button:has-text("Yes")', 
        'button:has-text("Confirm")',
        'button:has-text("Delete")',
        '.q-btn--unelevated:has-text("OK")'
      ];
      
      let confirmClicked = false;
      for (const selector of confirmButtons) {
        try {
          const confirmButton = page.locator(selector);
          if (await confirmButton.isVisible()) {
            await confirmButton.click();
            console.log(`✅ Clicked confirmation button: ${selector}`);
            confirmClicked = true;
            break;
          }
        } catch (e) {
          // Try next selector
        }
      }
      
      if (!confirmClicked) {
        console.log('⚠️ Could not find confirmation button, trying Enter key');
        await page.keyboard.press('Enter');
      }
      
    } catch (error) {
      console.log('⚠️ No confirmation dialog found, deletion may be immediate');
    }
    
    // Wait for deletion to process and table refresh
    await page.waitForTimeout(5000);
    
    // Step 6: Verify the deletion
    console.log('🔍 Verifying allowance deletion...');
    
    // Check if the allowance is gone
    const deletedRowExists = await allowanceRow.isVisible();
    
    if (!deletedRowExists) {
      console.log(`✅ SUCCESS! Allowance "${testData.nameToDelete}" has been deleted!`);
      
      // Count allowances after deletion
      const countAfter = await allRowsBefore.count();
      console.log(`📊 Found ${countAfter} allowances after deletion`);
      
      if (countAfter < countBefore) {
        console.log(`✅ Allowance count decreased from ${countBefore} to ${countAfter}`);
      } else {
        console.log(`⚠️ Allowance count unchanged: ${countBefore} -> ${countAfter}`);
      }
      
      await page.screenshot({ path: '/mnt/raid1/GitHub/allowance/tests/test-results/delete-allowance-success.png', fullPage: true });
      console.log('🎉 ALLOWANCE DELETE TEST PASSED! 🎉');
      process.exit(0); // Success
      
    } else {
      console.log(`❌ Allowance "${testData.nameToDelete}" still exists in table`);
      
      // Check for error messages
      const errorMessages = await page.locator('.q-notification--negative, .text-negative').allTextContents();
      if (errorMessages.length > 0) {
        console.log('🚨 Error messages found:', errorMessages);
      }
      
      await page.screenshot({ path: '/mnt/raid1/GitHub/allowance/tests/test-results/delete-allowance-failed.png', fullPage: true });
      process.exit(1); // Failure
    }
    
  } catch (error) {
    console.error('💥 Error:', error.message);
    await page.screenshot({ path: '/mnt/raid1/GitHub/allowance/tests/test-results/delete-allowance-error.png', fullPage: true });
    process.exit(1); // Failure
  } finally {
    await browser.close();
  }
})();