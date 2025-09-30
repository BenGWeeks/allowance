#!/usr/bin/env node
/**
 * Delete existing paylink for Receiving Wallet
 */

const { chromium } = require('playwright');
const { login, getConfig } = require('../auth-helper');

async function deletePaylink() {
  const browser = await chromium.launch({ headless: false });
  const page = await browser.newPage();
  const config = getConfig();
  const payLinkEmail = config.payLinkEmail;

  if (!payLinkEmail) {
    throw new Error('PAYLINK_EMAIL environment variable must be set');
  }

  try {
    // Login first
    await login(page);
    console.log('✓ Logged in successfully');

    // Navigate to Pay Links extension
    await page.goto(`${config.baseUrl}/lnurlp/`);
    await page.waitForTimeout(2000);
    console.log('✓ Navigated to Pay Links extension');

    // Look for the paylink to delete
    const username = payLinkEmail.split('@')[0];
    const paylink = page.locator(`tr:has-text("${username}")`).first();

    if (await paylink.isVisible({ timeout: 3000 }).catch(() => false)) {
      // Find and click the delete button for this paylink
      const deleteButton = paylink.locator('button[title="Delete"]').or(
        paylink.locator('button:has-text("Delete")').or(
          paylink.locator('.q-btn--round').last()
        )
      );

      if (await deleteButton.isVisible({ timeout: 2000 }).catch(() => false)) {
        await deleteButton.click();
        console.log('✓ Clicked delete button');

        // Confirm deletion in dialog if it appears
        await page.waitForTimeout(1000);
        const confirmButton = page.locator('button:has-text("DELETE")').or(
          page.locator('button:has-text("Confirm")')
        );

        if (await confirmButton.isVisible({ timeout: 2000 }).catch(() => false)) {
          await confirmButton.click();
          console.log('✓ Confirmed deletion');
        }

        // Wait for deletion to complete
        await page.waitForTimeout(2000);

        // Verify it's gone
        if (!await page.locator(`tr:has-text("${username}")`).isVisible({ timeout: 1000 }).catch(() => false)) {
          console.log(`✅ Successfully deleted paylink for ${username}`);
        }
      } else {
        console.log('⚠️ Delete button not found');
      }
    } else {
      console.log(`ℹ️ No paylink found for ${username}`);
    }

    await browser.close();
    return 0;

  } catch (error) {
    console.error('❌ Error deleting paylink:', error.message);
    await page.screenshot({ path: 'delete-paylink-error.png', fullPage: true });
    await browser.close();
    return 1;
  }
}

deletePaylink().then(exitCode => {
  process.exit(exitCode);
});