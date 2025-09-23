#!/usr/bin/env node
/**
 * Delete All Allowances
 * Deletes all existing allowances in the system
 */

const { chromium } = require('playwright');
const { login, getConfig } = require('./auth-helper');

async function deleteAllAllowances() {
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
    await page.screenshot({ path: 'delete-all-1-before.png', fullPage: true });

    // Count existing allowances
    const deleteButtons = page.locator('button[title="Delete allowance"], .q-btn:has(.q-icon:has-text("delete"))');
    const initialCount = await deleteButtons.count();

    if (initialCount === 0) {
      console.log('✓ No allowances to delete');
      await browser.close();
      return 0;
    }

    console.log(`Found ${initialCount} allowance(s) to delete`);
    let deletedCount = 0;

    // Delete each allowance
    while (await deleteButtons.first().isVisible()) {
      // Click the first delete button
      await deleteButtons.first().click();
      console.log(`  Deleting allowance ${deletedCount + 1}...`);

      // Wait for confirmation dialog if it appears
      const confirmButton = page.locator('.q-dialog button:has-text("Confirm"), .q-dialog button:has-text("Delete"), .q-dialog button:has-text("Yes")');
      if (await confirmButton.isVisible({ timeout: 2000 })) {
        await confirmButton.click();
        console.log(`  ✓ Confirmed deletion`);
      }

      // Wait for the row to be removed
      await page.waitForTimeout(1000);
      deletedCount++;

      // Check if there are more to delete
      if (deletedCount >= initialCount) {
        break; // Safety check to prevent infinite loop
      }
    }

    console.log(`✓ Deleted ${deletedCount} allowance(s)`);

    // Take final screenshot
    await page.screenshot({ path: 'delete-all-2-after.png', fullPage: true });

    // Verify all are deleted
    const remainingCount = await deleteButtons.count();
    if (remainingCount === 0) {
      console.log('✅ All allowances deleted successfully');
    } else {
      console.log(`⚠️ ${remainingCount} allowance(s) still remain`);
    }

    await browser.close();
    return 0;

  } catch (error) {
    console.error('❌ Error deleting allowances:', error);
    await page.screenshot({ path: 'delete-all-error.png', fullPage: true });
    await browser.close();
    return 1;
  }
}

// Run the script
deleteAllAllowances().then(exitCode => {
  process.exit(exitCode);
});