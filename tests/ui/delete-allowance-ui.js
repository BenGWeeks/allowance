#!/usr/bin/env node
/**
 * Test Delete Allowance - UI
 * Tests deleting allowances via the web interface using Playwright
 */

const { chromium } = require('playwright');
const { login, getConfig } = require('./auth-helper');

async function testDeleteUI() {
  const browser = await chromium.launch({
    headless: false,
    slowMo: 100
  });
  const context = await browser.newContext();
  const page = await context.newPage();
  const config = getConfig();

  try {
    console.log('🚀 Testing Allowance Deletion via UI');
    console.log('==========================================');

    // Step 1: Login
    console.log('📝 Step 1: Logging in...');
    await login(page);
    console.log('✓ Logged in successfully');

    // Step 2: Navigate to allowance page
    console.log('\n📝 Step 2: Navigating to allowance extension...');
    await page.goto(`${config.baseUrl}/allowance`);
    await page.waitForLoadState('networkidle');
    console.log('✓ Navigated to allowance extension');

    // Take initial screenshot
    await page.screenshot({ path: 'delete-ui-test-1-initial.png', fullPage: true });

    // Step 3: Count initial allowances
    console.log('\n📝 Step 3: Counting initial allowances...');
    const initialRows = await page.locator('tbody tr').count();
    console.log(`📊 Initial allowance count: ${initialRows}`);

    if (initialRows === 0) {
      console.log('⚠️ No allowances found to delete');
      await browser.close();
      return false;
    }

    // Step 4: Get details of first allowance
    console.log('\n📝 Step 4: Getting allowance details...');
    const firstRow = await page.locator('tbody tr').first();

    // Extract allowance details from table cells
    const cells = await firstRow.locator('td');
    const cellCount = await cells.count();
    console.log(`📋 Found ${cellCount} cells in row`);

    let allowanceName = 'Unknown';
    let allowanceAmount = 'Unknown';

    // Try to get name and amount (adjust indices based on table structure)
    try {
      if (cellCount >= 2) {
        allowanceName = await cells.nth(1).textContent() || 'Unknown';
        allowanceAmount = await cells.nth(2).textContent() || 'Unknown';
      }
    } catch (e) {
      console.log('⚠️ Could not extract allowance details from table');
    }

    console.log(`🎯 Target allowance: ${allowanceName}`);
    console.log(`   Amount: ${allowanceAmount}`);

    // Step 5: Click on the row to access actions
    console.log('\n📝 Step 5: Clicking on allowance row...');
    await firstRow.click();
    await page.waitForTimeout(1000);

    // Take screenshot after clicking row
    await page.screenshot({ path: 'delete-ui-test-2-row-clicked.png', fullPage: true });

    // Step 6: Look for delete button (with cancel icon and pink color)
    console.log('\n📝 Step 6: Finding delete button...');

    // Look for delete button with specific characteristics from your HTML
    let deleteButton = null;
    const buttonSelectors = [
      'button.text-pink:has(.q-icon:text("cancel"))',
      'button:has(.q-icon:text("cancel"))',
      'button.text-pink',
      'button:has([aria-hidden="true"]:text("cancel"))',
      '.q-btn--flat.text-pink',
      'tbody tr button.text-pink'
    ];

    for (const selector of buttonSelectors) {
      try {
        const buttons = await page.locator(selector);
        const count = await buttons.count();
        if (count > 0) {
          deleteButton = buttons.first();
          console.log(`✓ Found delete button using: ${selector} (${count} matches)`);
          break;
        }
      } catch (e) {
        continue;
      }
    }

    if (!deleteButton) {
      // Check if any buttons appeared after clicking the row
      const allButtons = await page.locator('button').all();
      console.log(`📋 Total buttons on page: ${allButtons.length}`);

      // Look for buttons with cancel icon
      const cancelButtons = await page.locator('button:has(.q-icon)').all();
      console.log(`📋 Buttons with icons: ${cancelButtons.length}`);

      for (let i = 0; i < cancelButtons.length; i++) {
        const button = cancelButtons[i];
        const iconText = await button.locator('.q-icon').textContent().catch(() => '');
        console.log(`   Button ${i + 1}: icon="${iconText}"`);

        if (iconText.includes('cancel') || iconText.includes('delete')) {
          deleteButton = button;
          console.log(`✓ Found delete button with ${iconText} icon`);
          break;
        }
      }
    }

    if (!deleteButton) {
      console.log('❌ Could not find delete button - taking debug screenshot');
      await page.screenshot({ path: 'delete-ui-debug.png', fullPage: true });
      await browser.close();
      return false;
    }

    // Step 7: Click delete button
    console.log('\n📝 Step 7: Clicking delete button...');
    await deleteButton.click();
    await page.waitForTimeout(1000);

    // Check if confirmation dialog appeared
    const confirmDialog = await page.locator('.q-dialog').first();
    if (await confirmDialog.isVisible()) {
      console.log('✓ Confirmation dialog appeared');

      // Take screenshot of confirmation
      await page.screenshot({ path: 'delete-ui-test-2-confirm.png', fullPage: true });

      // Look for confirm button
      const confirmButton = await page.locator('.q-dialog button:has-text("Delete"), .q-dialog button:has-text("Confirm"), .q-dialog button:has-text("Yes")').first();

      if (await confirmButton.isVisible()) {
        console.log('✓ Clicking confirmation button...');
        await confirmButton.click();
        await page.waitForTimeout(2000);
      } else {
        console.log('⚠️ No confirmation button found, pressing Enter...');
        await page.keyboard.press('Enter');
        await page.waitForTimeout(2000);
      }
    } else {
      console.log('⚠️ No confirmation dialog - delete may have executed immediately');
      await page.waitForTimeout(2000);
    }

    // Step 8: Verify deletion
    console.log('\n📝 Step 8: Verifying deletion...');

    // Reload page to ensure fresh data
    await page.reload();
    await page.waitForLoadState('networkidle');

    const finalRows = await page.locator('tbody tr').count();
    console.log(`📊 Final allowance count: ${finalRows}`);

    // Take final screenshot
    await page.screenshot({ path: 'delete-ui-test-3-final.png', fullPage: true });

    await browser.close();

    // Check if deletion was successful
    if (finalRows < initialRows) {
      console.log('✅ SUCCESS: Allowance deleted via UI');
      console.log(`📉 Count reduced from ${initialRows} to ${finalRows}`);
      return true;
    } else {
      console.log('❌ FAILED: Allowance count unchanged');
      console.log(`📊 Count: ${initialRows} → ${finalRows}`);
      return false;
    }

  } catch (error) {
    console.error('❌ UI deletion test failed:', error.message);
    await browser.close();
    return false;
  }
}

// Run if called directly
if (require.main === module) {
  testDeleteUI()
    .then(success => {
      if (success) {
        console.log('\n🎉 UI deletion test passed!');
        process.exit(0);
      } else {
        console.log('\n❌ UI deletion test failed!');
        process.exit(1);
      }
    })
    .catch(error => {
      console.error('❌ Test execution failed:', error);
      process.exit(1);
    });
}

module.exports = { testDeleteUI };