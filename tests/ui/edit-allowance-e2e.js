/**
 * End-to-end test: Create via API → Edit via UI → Verify via API
 * This tests the complete flow and ensures UI editing actually works
 */

const { chromium } = require('playwright');
const { login, getConfig } = require('./auth-helper');

(async () => {
  console.log('🧪 End-to-End Edit Allowance Test');
  console.log('===================================');

  const browser = await chromium.launch({ headless: true, slowMo: 500 });
  const page = await browser.newPage();
  const config = getConfig();

  try {
    // Step 1: Create allowance via API
    console.log('\n📝 Step 1: Creating allowance via API...');
    
    const { getAdminApiKey } = require('../get_api_key.js');
    const adminKey = await getAdminApiKey(page);
    
    if (!adminKey) {
      console.log('❌ Failed to get admin API key');
      process.exit(1);
    }
    
    // Create test allowance
    const createData = {
      name: 'E2E Test Allowance',
      lightning_address: 'e2etest@example.com',
      amount: 500,
      currency: 'sats',
      frequency_type: 'weekly',
      start_datetime: new Date().toISOString(),
      next_payment_date: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString(),
      active: true,
      memo: 'Created via API for UI editing test'
    };
    
    const createResponse = await page.request.post(`${config.baseUrl}/allowance/api/v1/allowance`, {
      headers: { 'X-Api-Key': adminKey },
      data: createData
    });
    
    if (!createResponse.ok()) {
      console.log(`❌ Failed to create allowance via API: ${createResponse.status()}`);
      process.exit(1);
    }
    
    const createdAllowance = await createResponse.json();
    const allowanceId = createdAllowance.id;
    console.log(`✅ Created allowance via API: ${allowanceId}`);
    console.log(`   Name: "${createData.name}"`);
    console.log(`   Amount: ${createData.amount} sats`);
    console.log(`   Active: ${createData.active}`);
    
    // Step 2: Login to UI
    console.log('\n📝 Step 2: Logging into UI...');
    await login(page);
    console.log('✅ Logged into UI');

    // Step 3: Navigate to allowance page and find our allowance
    console.log('\n📝 Step 3: Finding allowance in UI...');

    await page.goto(`${config.baseUrl}/allowance/`);
    await page.waitForTimeout(3000);
    
    // Find the allowance row
    const allowanceRow = page.locator(`tr:has-text("${createData.name}")`);
    const rowExists = await allowanceRow.count() > 0;
    
    if (!rowExists) {
      console.log('❌ Created allowance not found in UI table');
      process.exit(1);
    }
    
    console.log('✅ Found allowance in UI table');
    
    // Step 4: Edit the allowance via UI
    console.log('\n📝 Step 4: Editing allowance via UI...');
    
    // Look for edit button in the row (usually an icon or button)
    const editButton = allowanceRow.locator('button').first(); // Assuming first button is edit
    
    if (await editButton.isVisible()) {
      await editButton.click();
      await page.waitForTimeout(2000);
      
      // Update the form fields
      const newName = 'EDITED E2E Test Allowance';
      const newAmount = '750';
      const newAddress = 'edited-e2e@example.com';
      
      // Clear and fill name field
      const nameInput = page.locator('input[placeholder*="Weekly allowance"], input').first();
      await nameInput.clear();
      await nameInput.fill(newName);
      
      // Clear and fill amount field
      const amountInput = page.locator('input[type="number"]');
      await amountInput.clear();
      await amountInput.fill(newAmount);
      
      // Clear and fill lightning address field
      const addressInput = page.locator('input[placeholder*="alice@getalby.com"], input[placeholder*="@"]');
      if (await addressInput.count() > 0) {
        await addressInput.clear();
        await addressInput.fill(newAddress);
      }
      
      // Toggle active status (set to false)
      const activeToggle = page.locator('input[type="checkbox"], .q-toggle');
      if (await activeToggle.count() > 0) {
        await activeToggle.click(); // Toggle to inactive
      }
      
      console.log(`   Updated name: "${newName}"`);
      console.log(`   Updated amount: ${newAmount} sats`);
      console.log(`   Updated address: ${newAddress}`);
      console.log(`   Updated active: false`);
      
      // Submit the form
      const submitButton = page.locator('button:has-text("Update"), button:has-text("Save")');
      if (await submitButton.count() > 0) {
        await submitButton.click();
        await page.waitForTimeout(3000);
        console.log('✅ Submitted edit form');
      } else {
        console.log('⚠️ Submit button not found, trying generic button');
        await page.locator('button').last().click();
        await page.waitForTimeout(3000);
      }
      
    } else {
      console.log('❌ Edit button not found in allowance row');
      process.exit(1);
    }
    
    // Step 5: Verify changes via API
    console.log('\n📝 Step 5: Verifying changes via API...');
    
    const verifyResponse = await page.request.get(`${config.baseUrl}/allowance/api/v1/allowance`, {
      headers: { 'X-Api-Key': adminKey }
    });
    
    if (!verifyResponse.ok()) {
      console.log(`❌ Failed to fetch allowances for verification: ${verifyResponse.status()}`);
      process.exit(1);
    }
    
    const allowances = await verifyResponse.json();
    const updatedAllowance = allowances.find(a => a.id === allowanceId);
    
    if (!updatedAllowance) {
      console.log('❌ Updated allowance not found via API');
      process.exit(1);
    }
    
    // Check if changes were applied
    let changesApplied = true;
    const results = [];
    
    if (updatedAllowance.name === 'EDITED E2E Test Allowance') {
      results.push('✅ Name updated correctly');
    } else {
      results.push(`❌ Name not updated: expected "EDITED E2E Test Allowance", got "${updatedAllowance.name}"`);
      changesApplied = false;
    }
    
    if (updatedAllowance.amount === 750) {
      results.push('✅ Amount updated correctly');
    } else {
      results.push(`❌ Amount not updated: expected 750, got ${updatedAllowance.amount}`);
      changesApplied = false;
    }
    
    if (updatedAllowance.lightning_address === 'edited-e2e@example.com') {
      results.push('✅ Lightning address updated correctly');
    } else {
      results.push(`❌ Address not updated: expected "edited-e2e@example.com", got "${updatedAllowance.lightning_address}"`);
      changesApplied = false;
    }
    
    if (updatedAllowance.active === false) {
      results.push('✅ Active status updated correctly');
    } else {
      results.push(`❌ Active status not updated: expected false, got ${updatedAllowance.active}`);
      changesApplied = false;
    }
    
    // Display results
    console.log('\n🎯 VERIFICATION RESULTS:');
    results.forEach(result => console.log(`   ${result}`));
    
    if (changesApplied) {
      console.log('\n🎉 END-TO-END EDIT TEST PASSED!');
      console.log('✅ API Create → UI Edit → API Verify: ALL WORKING!');
      process.exit(0);
    } else {
      console.log('\n💥 END-TO-END EDIT TEST FAILED!');
      console.log('❌ Some changes were not applied correctly');
      process.exit(1);
    }
    
  } catch (error) {
    console.error('💥 Error:', error.message);
    await page.screenshot({ path: 'tests/test-results/e2e-edit-error.png', fullPage: true });
    process.exit(1);
  } finally {
    await browser.close();
  }
})();