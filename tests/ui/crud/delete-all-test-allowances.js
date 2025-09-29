#!/usr/bin/env node
/**
 * Delete All Test Allowances
 * Deletes only allowances with "Test" or "TEST" in their name
 */

const { chromium } = require('playwright');
const { login, getConfig } = require('../auth-helper');

async function deleteAllTestAllowances() {
  const browser = await chromium.launch({
    headless: false,
    slowMo: 50
  });
  const context = await browser.newContext();
  const page = await context.newPage();
  const config = getConfig();

  try {
    // Login first
    await login(page);
    console.log('✓ Logged in successfully');

    // Navigate to Allowance extension
    await page.goto(`${config.baseUrl}/allowance`);
    await page.waitForLoadState('networkidle');
    console.log('✓ Navigated to Allowance extension');

    // Take initial screenshot
    await page.screenshot({ path: 'delete-all-test-1-before.png', fullPage: true });

    // Find all rows that contain "Test" or "TEST" in the name
    const allRows = await page.locator('tbody tr').all();
    let testAllowances = [];

    for (let i = 0; i < allRows.length; i++) {
      const nameCell = await allRows[i].locator('td').first().textContent();
      if (nameCell && (nameCell.includes('Test') || nameCell.includes('TEST'))) {
        testAllowances.push(i);
      }
    }

    if (testAllowances.length === 0) {
      console.log('✓ No test allowances to delete');
      await browser.close();
      return 0;
    }

    console.log(`Found ${testAllowances.length} test allowance(s) to delete`);
    let deletedCount = 0;

    // Delete each test allowance (go backwards to avoid index shifting)
    for (let i = testAllowances.length - 1; i >= 0; i--) {
      const rows = await page.locator('tbody tr').all();

      // Find the row with Test in the name
      for (let j = 0; j < rows.length; j++) {
        const nameCell = await rows[j].locator('td').first().textContent();
        if (nameCell && (nameCell.includes('Test') || nameCell.includes('TEST'))) {
          // Find delete button in this row
          const deleteButton = rows[j].locator('button[title="Delete allowance"], .q-btn:has(.q-icon:has-text("delete"))');

          if (await deleteButton.isVisible()) {
            console.log(`  Deleting test allowance: ${nameCell.trim()}`);
            await deleteButton.click();

            // Wait for confirmation dialog if it appears
            const confirmButton = page.locator('.q-dialog button:has-text("Confirm"), .q-dialog button:has-text("Delete"), .q-dialog button:has-text("Yes")');
            if (await confirmButton.isVisible({ timeout: 2000 })) {
              await confirmButton.click();
              console.log(`  ✓ Confirmed deletion`);
            }

            // Wait for the row to be removed
            await page.waitForTimeout(1000);
            deletedCount++;
            break; // Move to next test allowance
          }
        }
      }
    }

    console.log(`✓ Deleted ${deletedCount} test allowance(s)`);

    // Take final screenshot
    await page.screenshot({ path: 'delete-all-test-2-after.png', fullPage: true });

    // Check if any test allowances remain
    const remainingRows = await page.locator('tbody tr').all();
    let remainingTestCount = 0;
    for (let i = 0; i < remainingRows.length; i++) {
      const nameCell = await remainingRows[i].locator('td').first().textContent();
      if (nameCell && (nameCell.includes('Test') || nameCell.includes('TEST'))) {
        remainingTestCount++;
      }
    }

    if (remainingTestCount === 0) {
      console.log('✅ All test allowances deleted successfully');
    } else {
      console.log(`⚠️ ${remainingTestCount} test allowance(s) still remain`);
    }

    await browser.close();
    return 0;

  } catch (error) {
    console.error('❌ Error deleting test allowances:', error);
    await page.screenshot({ path: 'delete-all-test-error.png', fullPage: true });
    await browser.close();
    return 1;
  }
}

// Run the script
deleteAllTestAllowances().then(exitCode => {
  process.exit(exitCode);
});