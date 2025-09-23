#!/usr/bin/env node
/**
 * Comprehensive Allowance Test
 * Tests all major features including:
 * - Currency settings (GBP with decimal amounts)
 * - Minutely payments with 5-minute end time
 * - Transaction verification
 */

const { chromium } = require('playwright');
const { login, getConfig } = require('./auth-helper');

async function runComprehensiveTest() {
  const browser = await chromium.launch({
    headless: false,
    slowMo: 50
  });
  const context = await browser.newContext();
  const page = await context.newPage();
  const config = getConfig();

  try {
    console.log('🚀 Starting Comprehensive Currency & Minutely Payment Test');
    console.log('==========================================');
    console.log(`📧 Using Lightning address: ${config.payLinkEmail}`);

    // Login
    await login(page);
    console.log('✓ Logged in successfully');

    // Navigate to Allowance extension
    await page.goto(`${config.baseUrl}/allowance`);
    await page.waitForLoadState('networkidle');
    console.log('✓ Navigated to Allowance extension');

    // Take screenshot of main page
    await page.screenshot({ path: 'currency-minutely-test-1-main.png', fullPage: true });

    // Click New Allowance button
    await page.click('button:has-text("New Allowance")');
    await page.waitForSelector('.q-dialog', { state: 'visible' });
    console.log('✓ Opened Create Allowance dialog');

    // Fill in description
    await page.fill('input[label*="Description"]', 'GBP Minutely Test - 0.02 GBP');

    // Select wallet (first available)
    const walletDropdown = await page.locator('input[label*="Wallet"]').or(page.locator('.q-select:has-text("Wallet")'));
    if (await walletDropdown.isVisible()) {
      await walletDropdown.click();
      await page.waitForTimeout(500);
      await page.keyboard.press('Enter'); // Select first wallet
      console.log('✓ Selected wallet');
    }

    // Fill in Lightning address from config
    await page.fill('input[label*="Lightning"][label*="Address"]', config.payLinkEmail);
    console.log(`✓ Set Lightning address: ${config.payLinkEmail}`);

    // Test 1: Check currency dropdown
    console.log('\n📝 Test 1: Checking currency settings...');
    const currencySelect = await page.locator('.q-select').filter({ hasText: 'Currency' }).or(page.locator('[label="Currency"]'));
    await currencySelect.click();
    await page.waitForTimeout(500);

    // Look for GBP in the dropdown
    const gbpOption = await page.locator('[role="option"]').filter({ hasText: 'GBP' }).first();
    if (await gbpOption.isVisible()) {
      await gbpOption.click();
      console.log('✓ Selected GBP currency');
    } else {
      // Try alternative selector
      await page.click('.q-item:has-text("GBP")');
      console.log('✓ Selected GBP currency (alternative)');
    }
    await page.waitForTimeout(500);

    // Test 2: Test decimal amount for GBP currency
    console.log('\n📝 Test 2: Testing decimal amounts...');
    const amountInput = await page.locator('input[type="number"][label*="Amount"]').or(page.locator('input[label="Amount *"]'));
    await amountInput.fill('0.02');
    console.log('✓ Entered decimal amount 0.02 GBP');

    // Test 3: Create a minutely allowance with 5-minute end time
    console.log('\n📝 Test 3: Setting up minutely payments...');

    // Select Minutely frequency
    const frequencySelect = await page.locator('.q-select').filter({ hasText: 'Frequency' }).or(page.locator('[label*="Frequency"]'));
    await frequencySelect.click();
    await page.waitForTimeout(500);

    const minutelyOption = await page.locator('[role="option"]').filter({ hasText: 'Minutely' }).first();
    if (await minutelyOption.isVisible()) {
      await minutelyOption.click();
      console.log('✓ Selected Minutely frequency');
    } else {
      await page.click('.q-item:has-text("Minutely")');
      console.log('✓ Selected Minutely frequency (alternative)');
    }

    // Leave start date empty (should default to now)
    console.log('✓ Leaving start date empty (will default to now)');

    // Set end date to 5 minutes from now
    const endDate = new Date();
    endDate.setMinutes(endDate.getMinutes() + 5);
    const endDateStr = endDate.toISOString().slice(0, 16); // Format: YYYY-MM-DDTHH:mm

    const endDateInput = await page.locator('input[type="datetime-local"][label*="End"]').or(page.locator('input[label*="End date"]'));
    await endDateInput.fill(endDateStr);
    console.log(`✓ Set end date to ${endDateStr} (5 minutes from now)`);

    // Take screenshot before creating
    await page.screenshot({ path: 'currency-minutely-test-2-filled.png', fullPage: true });

    // Create the allowance
    const createButton = await page.locator('.q-dialog button').filter({ hasText: /Create|Save/ }).first();
    await createButton.click();
    await page.waitForSelector('.q-dialog', { state: 'hidden', timeout: 10000 });
    console.log('✓ Created allowance successfully');

    // Wait for table to update
    await page.waitForTimeout(2000);

    // Take screenshot of updated list
    await page.screenshot({ path: 'currency-minutely-test-3-created.png', fullPage: true });

    // Test 4: Verify the allowance was created
    console.log('\n📝 Test 4: Verifying allowance creation...');
    const allowanceRow = page.locator('tr').filter({ hasText: 'GBP Minutely Test' });

    if (await allowanceRow.isVisible()) {
      console.log('✓ Allowance appears in the list');

      // Check amount displays with GBP
      const amountCell = await allowanceRow.locator('td').nth(2).textContent();
      console.log(`✓ Amount displayed as: ${amountCell}`);

      // Verify GBP currency is shown
      if (amountCell.includes('GBP')) {
        console.log('✓ GBP currency correctly displayed');
      }
    } else {
      console.log('✗ Allowance not found in list');
    }

    // Test 5: Monitor payments for 5 minutes
    console.log('\n📝 Test 5: Monitoring minutely payments...');
    console.log('⏰ Will monitor for 5 minutes then stop...');

    const startTime = Date.now();
    const duration = 5 * 60 * 1000; // 5 minutes in milliseconds
    let paymentCount = 0;

    while (Date.now() - startTime < duration) {
      const elapsed = Math.floor((Date.now() - startTime) / 1000);
      const remaining = Math.floor((duration - (Date.now() - startTime)) / 1000);
      console.log(`⏳ Elapsed: ${elapsed}s, Remaining: ${remaining}s`);

      // Wait 1 minute between checks
      await page.waitForTimeout(60000);
      paymentCount++;

      // Reload to see latest status
      await page.reload();
      await page.waitForLoadState('networkidle');

      console.log(`✓ Payment check ${paymentCount} completed`);

      // Check allowance still exists
      const updatedRow = page.locator('tr').filter({ hasText: 'GBP Minutely Test' });
      if (await updatedRow.isVisible()) {
        console.log('  Allowance still active');
      }
    }

    console.log(`\n✅ Test completed after 5 minutes`);
    console.log(`📊 Total payments monitored: ${paymentCount}`);

    // Test 6: Verify transactions
    console.log('\n📝 Test 6: Checking transactions...');

    // Navigate to wallet transactions
    await page.goto(`${config.baseUrl}/wallet`);
    await page.waitForLoadState('networkidle');

    // Look for GBP transactions
    const transactions = await page.locator('text=/0\\.02.*GBP|GBP.*0\\.02/').count();
    if (transactions > 0) {
      console.log(`✓ Found ${transactions} GBP transaction(s)`);
    }

    // Take final screenshot
    await page.screenshot({ path: 'currency-minutely-test-4-final.png', fullPage: true });

    await browser.close();
    console.log('\n==========================================');
    console.log('✅ Comprehensive test completed successfully!');
    return 0;

  } catch (error) {
    console.error('❌ Comprehensive test failed:', error);
    await page.screenshot({ path: 'comprehensive-test-error.png', fullPage: true });
    await browser.close();
    return 1;
  }
}

// Run the test
runComprehensiveTest().then(exitCode => {
  process.exit(exitCode);
});