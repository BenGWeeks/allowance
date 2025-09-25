#!/usr/bin/env node
/**
 * Test Date Persistence
 * Verifies that when you update an allowance with future dates,
 * those dates are preserved when you edit it again
 */

const { chromium } = require('playwright');
const { login, getConfig } = require('./auth-helper');

async function testDatePersistence() {
  const browser = await chromium.launch({
    headless: false,
    slowMo: 100
  });
  const context = await browser.newContext();
  const page = await context.newPage();
  const config = getConfig();

  try {
    console.log('🚀 Testing Date Persistence');
    console.log('==========================================');

    // Login
    await login(page);
    console.log('✓ Logged in successfully');

    // Navigate to Allowance extension
    await page.goto(`${config.baseUrl}/allowance`);
    await page.waitForLoadState('networkidle');
    console.log('✓ Navigated to Allowance extension');

    // Find the first allowance row
    const firstRow = await page.locator('tbody tr').first();
    if (!await firstRow.isVisible()) {
      console.log('❌ No allowances found to test');
      process.exit(1);
    }

    // Get allowance ID for tracking
    const allowanceId = await firstRow.locator('td').first().textContent();
    console.log(`\n📋 Testing allowance: ${allowanceId}`);

    // STEP 1: Open edit dialog and check current dates
    console.log('\n🔍 STEP 1: Check current dates');
    const editButton = firstRow.locator('button:has(.q-icon:text("edit"))').first();
    await editButton.click();
    await page.waitForSelector('.q-dialog', { state: 'visible' });

    const startInput = page.locator('input[type="datetime-local"]').nth(0);
    const endInput = page.locator('input[type="datetime-local"]').nth(1);

    const originalStart = await startInput.inputValue();
    const originalEnd = await endInput.inputValue();

    console.log(`  Original Start: ${originalStart}`);
    console.log(`  Original End: ${originalEnd}`);

    // STEP 2: Update to future dates
    console.log('\n📝 STEP 2: Update to future dates');
    const futureDate = new Date();
    futureDate.setDate(futureDate.getDate() + 7); // 7 days from now
    const futureStart = futureDate.toISOString().slice(0, 16);

    futureDate.setHours(futureDate.getHours() + 2); // 2 hours after start
    const futureEnd = futureDate.toISOString().slice(0, 16);

    console.log(`  New Start: ${futureStart}`);
    console.log(`  New End: ${futureEnd}`);

    // Clear and fill new dates
    await startInput.fill(futureStart);
    await endInput.fill(futureEnd);

    // Save changes
    const updateButton = page.locator('.q-dialog button:has-text("Update Allowance")').first();
    await updateButton.click();
    console.log('  ✓ Clicked Update Allowance');

    // Wait for dialog to close
    await page.waitForSelector('.q-dialog', { state: 'hidden', timeout: 5000 });
    await page.waitForTimeout(2000);

    // STEP 3: Refresh page to ensure we get fresh data
    console.log('\n🔄 STEP 3: Refresh and re-open edit dialog');
    await page.reload();
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);

    // Find the same allowance again (might have moved position)
    const rowsAfterRefresh = await page.locator('tbody tr').all();
    let targetRow = null;
    for (const row of rowsAfterRefresh) {
      const cellText = await row.locator('td').first().textContent();
      if (cellText.includes(allowanceId.trim())) {
        targetRow = row;
        break;
      }
    }

    if (!targetRow) {
      console.log('❌ Could not find allowance after refresh');
      process.exit(1);
    }

    // Open edit dialog again
    const editButtonAgain = targetRow.locator('button:has(.q-icon:text("edit"))').first();
    await editButtonAgain.click();
    await page.waitForSelector('.q-dialog', { state: 'visible' });

    // STEP 4: Check if dates persisted
    console.log('\n✅ STEP 4: Verify dates persisted');
    const startInputAfter = page.locator('input[type="datetime-local"]').nth(0);
    const endInputAfter = page.locator('input[type="datetime-local"]').nth(1);

    const displayedStart = await startInputAfter.inputValue();
    const displayedEnd = await endInputAfter.inputValue();

    console.log(`  Displayed Start: ${displayedStart}`);
    console.log(`  Displayed End: ${displayedEnd}`);
    console.log(`  Expected Start: ${futureStart}`);
    console.log(`  Expected End: ${futureEnd}`);

    // Check if dates match
    if (displayedStart === futureStart && displayedEnd === futureEnd) {
      console.log('\n✅ SUCCESS: Future dates persisted correctly!');
    } else if (displayedStart === originalStart && displayedEnd === originalEnd) {
      console.log('\n❌ FAILURE: Dates reverted to original values!');
      console.log('   The update was not saved properly.');
      process.exit(1);
    } else {
      console.log('\n⚠️ WARNING: Dates changed but not to expected values');
      console.log('   This might indicate a timezone conversion issue.');

      // Check if it's a timezone offset issue
      const expectedDate = new Date(futureStart);
      const displayedDate = new Date(displayedStart);
      const hoursDiff = Math.abs(expectedDate - displayedDate) / 3600000;

      if (hoursDiff > 0 && hoursDiff <= 24) {
        console.log(`   Possible timezone offset: ${hoursDiff} hours`);
      }
      process.exit(1);
    }

    await browser.close();
    console.log('\n✅ Date persistence test completed successfully!');
    process.exit(0);

  } catch (error) {
    console.error('❌ Test failed:', error.message);
    await page.screenshot({ path: 'test-screenshots/date-persistence-error.png', fullPage: true });
    await browser.close();
    process.exit(1);
  }
}

// Run the test
testDatePersistence();