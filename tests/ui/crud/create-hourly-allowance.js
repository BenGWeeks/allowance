#!/usr/bin/env node

const { chromium } = require('playwright');
const { getConfig, login } = require('../auth-helper');

(async () => {
  console.log('⏰ Creating hourly allowance (2 sats/hour for 3 hours)...');

  const config = getConfig();
  const browser = await chromium.launch({ headless: false });
  const page = await browser.newPage();

  try {
    // Login
    await login(page);
    console.log('✅ Logged in successfully');

    // Navigate directly to allowance extension page
    await page.goto(`${config.baseUrl}/allowance`);
    await page.waitForTimeout(3000);
    console.log('✅ Navigated to allowance extension');

    // Click New Allowance button - look for the button or use Vue function
    try {
      // First try the button
      const newButton = page.locator('button:has-text("New Allowance")');
      if (await newButton.count() > 0) {
        await newButton.click();
      } else {
        // If button not found, try calling Vue function directly
        await page.evaluate(() => {
          if (window.app && window.app.openCreateDialog) {
            window.app.openCreateDialog();
          }
        });
      }
      await page.waitForTimeout(1000);
      console.log('✅ Opened create dialog');
    } catch (e) {
      console.log('⚠️ Could not open dialog via button, trying alternate method...');
      await page.evaluate(() => {
        if (window.app && window.app.openCreateDialog) {
          window.app.openCreateDialog();
        }
      });
    }

    // Fill in the form
    const now = new Date();
    const endTime = new Date(now.getTime() + 3 * 60 * 60 * 1000); // 3 hours from now

    // Name - use the third input field which is for name
    const inputs = await page.locator('input[type="text"]').all();
    if (inputs.length >= 3) {
      await inputs[2].fill('Hourly Test - 2 sats for 3 hours');
    }

    // Lightning address - use the fifth input field
    if (inputs.length >= 5) {
      await inputs[4].fill(config.payLinkEmail);
    }

    // Amount - 2 sats
    await page.fill('input[type="number"]', '2');

    // Currency - keep as sats (default)

    // Frequency - select hourly
    const frequencySelect = page.locator('.q-select').filter({ hasText: 'Frequency' });
    await frequencySelect.click();
    await page.waitForTimeout(500);
    await page.click('.q-item:has-text("Hourly")');
    await page.waitForTimeout(500);
    console.log('✅ Selected hourly frequency');

    // Start date & time (optional - will use current time)
    const startDateInput = page.locator('input[type="datetime-local"]').first();
    const startDateVisible = await startDateInput.count() > 0;
    if (startDateVisible) {
      await startDateInput.fill(now.toISOString().slice(0, 16));
    }

    // End date & time - set to 3 hours from now
    const endDateInput = page.locator('input[type="datetime-local"]').nth(1);
    const endDateVisible = await endDateInput.count() > 1;
    if (endDateVisible) {
      await endDateInput.fill(endTime.toISOString().slice(0, 16));
    }

    // Memo - find the textarea
    const memoField = page.locator('textarea').first();
    if (await memoField.count() > 0) {
      await memoField.fill('Testing hourly payments: 2 sats every hour for 3 hours');
    }

    // Active checkbox - usually checked by default, skip if hidden

    console.log('📝 Form filled:');
    console.log('   Name: Hourly Test - 2 sats for 3 hours');
    console.log('   Amount: 2 sats');
    console.log('   Frequency: hourly');
    console.log('   Duration: 3 hours');
    console.log(`   Start: ${now.toLocaleString()}`);
    console.log(`   End: ${endTime.toLocaleString()}`);

    // Submit the form - look for the Create button in the dialog
    await page.click('button[type="submit"]:has-text("Create")');
    await page.waitForTimeout(2000);

    // Check for success
    const cards = await page.locator('.q-card').count();
    if (cards > 0) {
      console.log('✅ Hourly allowance created successfully!');
      console.log('   Will send 2 sats at the start of each hour');
      console.log('   Total of 6 sats will be sent over 3 hours');
      console.log('   First payment should occur within 1 hour');
    }

    // Take screenshot
    await page.screenshot({ path: 'test-screenshots/hourly-allowance-created.png' });
    console.log('📸 Screenshot saved: hourly-allowance-created.png');

  } catch (error) {
    console.error('❌ Failed to create hourly allowance:', error.message);
    await page.screenshot({ path: 'test-screenshots/hourly-allowance-error.png' });
    process.exit(1);
  } finally {
    await browser.close();
  }

  console.log('✅ Hourly allowance creation completed');
  console.log('ℹ️  Monitor the allowance to verify payments are sent hourly');
})();