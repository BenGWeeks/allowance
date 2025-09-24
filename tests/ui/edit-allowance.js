#!/usr/bin/env node
/**
 * Test Edit Metadata
 * Verifies that all allowance metadata (start date, end date, etc.)
 * is properly displayed when editing an allowance
 */

const { chromium } = require('playwright');
const { login, getConfig } = require('./auth-helper');

async function testEditMetadata() {
  const browser = await chromium.launch({
    headless: false,
    slowMo: 100
  });
  const context = await browser.newContext();
  const page = await context.newPage();
  const config = getConfig();

  try {
    console.log('🚀 Starting Edit Metadata Test');
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

    // Get allowance details from table (adjust based on table structure)
    const cells = await firstRow.locator('td');
    const cellCount = await cells.count();
    console.log(`📋 Found ${cellCount} cells in table row`);

    let allowanceInfo = {};
    try {
      // Extract what we can from the visible cells
      if (cellCount >= 4) {
        allowanceInfo.description = await cells.nth(0).textContent() || 'N/A';
        allowanceInfo.amount = await cells.nth(1).textContent() || 'N/A';
        allowanceInfo.recipient = await cells.nth(2).textContent() || 'N/A';
        allowanceInfo.frequency = await cells.nth(3).textContent() || 'N/A';
      }
    } catch (e) {
      console.log('⚠️ Could not extract all table data');
    }

    console.log('\n📋 Testing edit for allowance:');
    console.log(`  Description: ${allowanceInfo.description}`);
    console.log(`  Amount: ${allowanceInfo.amount}`);
    console.log(`  Recipient: ${allowanceInfo.recipient}`);
    console.log(`  Frequency: ${allowanceInfo.frequency}`);

    // Click on the row first to activate it
    await firstRow.click();
    await page.waitForTimeout(500);

    // Look for edit button (likely has edit icon)
    let editButton = null;
    const editSelectors = [
      'button:has(.q-icon:text("edit"))',
      'button:has(.q-icon:text("create"))',
      'button.text-blue',
      'tbody tr button.text-blue',
      'button:not(.text-pink)'  // Not the delete button
    ];

    for (const selector of editSelectors) {
      try {
        const buttons = await page.locator(selector);
        const count = await buttons.count();
        if (count > 0) {
          editButton = buttons.first();
          console.log(`✓ Found edit button using: ${selector}`);
          break;
        }
      } catch (e) {
        continue;
      }
    }

    if (!editButton) {
      // Check all buttons with icons
      const iconButtons = await page.locator('tbody tr button:has(.q-icon)').all();
      console.log(`📋 Found ${iconButtons.length} buttons with icons`);

      for (let i = 0; i < iconButtons.length; i++) {
        const button = iconButtons[i];
        const iconText = await button.locator('.q-icon').textContent().catch(() => '');
        const className = await button.getAttribute('class') || '';
        console.log(`   Button ${i + 1}: icon="${iconText}", class="${className}"`);

        if (iconText.includes('edit') || iconText.includes('create') || className.includes('text-blue')) {
          editButton = button;
          console.log(`✓ Using button with ${iconText} icon as edit button`);
          break;
        }
      }
    }

    if (!editButton) {
      console.log('❌ Could not find edit button');
      await page.screenshot({ path: 'test-screenshots/edit-metadata-no-button.png', fullPage: true });
      process.exit(1);
    }

    // Click edit button
    await editButton.click();
    await page.waitForSelector('.q-dialog', { state: 'visible' });
    console.log('\n✓ Edit dialog opened');

    // Check all fields are populated
    console.log('\n🔍 Checking form fields:');

    // Check each input field
    const inputs = await page.locator('.q-dialog input');
    const inputCount = await inputs.count();
    console.log(`  Found ${inputCount} input fields`);

    for (let i = 0; i < inputCount; i++) {
      const input = inputs.nth(i);
      const value = await input.inputValue();
      const type = await input.getAttribute('type');
      const label = await input.getAttribute('aria-label') || await input.getAttribute('label') || `Input ${i}`;

      if (value) {
        console.log(`  ✓ ${label} (${type}): ${value}`);
      } else {
        console.log(`  ⚠️ ${label} (${type}): EMPTY`);
      }
    }

    // Specifically check datetime fields
    console.log('\n📅 Checking datetime fields:');

    const datetimeInputs = await page.locator('.q-dialog input[type="datetime-local"]');
    const datetimeCount = await datetimeInputs.count();

    let datetimeSuccess = true;
    if (datetimeCount > 0) {
      for (let i = 0; i < datetimeCount; i++) {
        const input = datetimeInputs.nth(i);
        const value = await input.inputValue();
        const label = await input.getAttribute('label') || '';

        if (i === 0) {
          // Start datetime is required and should be populated
          if (value && value !== '') {
            console.log(`  ✅ Start datetime: ${value} (format: YYYY-MM-DDTHH:MM)`);
          } else {
            console.log(`  ❌ Start datetime: EMPTY - This should be populated!`);
            datetimeSuccess = false;
          }
        } else if (i === 1) {
          // End datetime is optional
          if (value && value !== '') {
            console.log(`  ✅ End datetime: ${value} (format: YYYY-MM-DDTHH:MM)`);
          } else {
            console.log(`  ℹ️ End datetime: Not set (optional field)`);
          }
        }
      }
    } else {
      console.log('  ❌ No datetime-local inputs found!');
    }

    // Check select dropdowns
    console.log('\n📝 Checking select fields:');
    const selects = await page.locator('.q-dialog .q-select');
    const selectCount = await selects.count();

    for (let i = 0; i < selectCount; i++) {
      const select = selects.nth(i);
      const value = await select.locator('.q-field__native span').textContent().catch(() => '');
      const label = await select.getAttribute('aria-label') || `Select ${i}`;

      if (value && value.trim()) {
        console.log(`  ✓ ${label}: ${value}`);
      } else {
        console.log(`  ⚠️ ${label}: NOT SET`);
      }
    }

    // Check toggle/checkbox for Active status
    console.log('\n🔘 Checking Active status:');
    const toggle = await page.locator('.q-dialog .q-toggle');
    if (await toggle.isVisible()) {
      const isActive = await toggle.evaluate(el => el.classList.contains('q-toggle--truthy'));
      console.log(`  ✓ Active status: ${isActive ? 'ON' : 'OFF'}`);
    } else {
      console.log('  ⚠️ Active toggle not found');
    }

    // Test editing the active status
    console.log('\n🔄 Testing Active status persistence:');

    // Toggle the active status if it exists
    const activeToggle = await page.locator('.q-dialog .q-toggle').first();
    if (await activeToggle.isVisible()) {
      const wasActive = await activeToggle.evaluate(el => el.classList.contains('q-toggle--truthy'));
      console.log(`  Current status: ${wasActive ? 'ACTIVE' : 'INACTIVE'}`);

      // Toggle to opposite state
      await activeToggle.click();
      await page.waitForTimeout(500);

      const shouldBeActive = !wasActive;
      console.log(`  Changed to: ${shouldBeActive ? 'ACTIVE' : 'INACTIVE'}`);

      // Save the changes
      const updateButton = page.locator('.q-dialog button:has-text("Update Allowance")').first();
      if (await updateButton.isVisible()) {
        await updateButton.click();
        console.log('  ✓ Clicked Update Allowance');
        await page.waitForTimeout(2000);

        // Refresh the page to reload data
        await page.reload();
        await page.waitForLoadState('networkidle');
        console.log('  ✓ Page refreshed');
        await page.waitForTimeout(2000);

        // Open edit dialog again to check if status persisted
        const editButtonAgain = firstRow.locator('button').filter({ hasText: 'edit' }).or(firstRow.locator('button:has(.q-icon:text("edit"))')).first();
        await editButtonAgain.click();
        await page.waitForSelector('.q-dialog', { state: 'visible' });
        console.log('  ✓ Re-opened edit dialog');

        // Check if active status persisted
        const activeToggleAfter = await page.locator('.q-dialog .q-toggle').first();
        const isActiveAfter = await activeToggleAfter.evaluate(el => el.classList.contains('q-toggle--truthy'));

        if (isActiveAfter === shouldBeActive) {
          console.log(`  ✅ Active status persisted correctly: ${isActiveAfter ? 'ACTIVE' : 'INACTIVE'}`);
        } else {
          console.log(`  ❌ Active status DID NOT persist!`);
          console.log(`     Expected: ${shouldBeActive ? 'ACTIVE' : 'INACTIVE'}`);
          console.log(`     Got: ${isActiveAfter ? 'ACTIVE' : 'INACTIVE'}`);
          datetimeSuccess = false; // Mark test as failed
        }
      }
    }

    // Take screenshot of edit form
    await page.screenshot({ path: 'test-screenshots/edit-metadata-test.png', fullPage: true });
    console.log('\n📸 Screenshot saved: edit-metadata-test.png');

    // Close dialog
    await page.keyboard.press('Escape');
    await page.waitForSelector('.q-dialog', { state: 'hidden' });

    await browser.close();

    // Check if datetime fields passed validation
    if (!datetimeSuccess) {
      console.log('\n❌ Edit metadata test FAILED - datetime fields are not populated!');
      process.exit(1);
    } else {
      console.log('\n✅ Edit metadata test completed successfully!');
      process.exit(0);
    }

  } catch (error) {
    console.error('❌ Test failed:', error.message);
    await browser.close();
    process.exit(1);
  }
}

// Run the test
testEditMetadata();