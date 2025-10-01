#!/usr/bin/env node

const { chromium } = require('playwright');
const { getConfig, login } = require('../auth-helper');

// Helper to convert Date to Quasar datetime format "YYYY-MM-DD HH:mm"
function toQuasarDatetimeString(date) {
  const offset = date.getTimezoneOffset() * 60000;
  const localDate = new Date(date.getTime() - offset);
  const isoString = localDate.toISOString();
  return isoString.slice(0, 16).replace('T', ' ');
}

// Helper to set datetime using Quasar date/time pickers
async function setQuasarDatetime(page, labelText, datetimeValue) {
  // Find the input by its label
  const input = page.locator(`input[data-cy="end-datetime-input"]`);

  // Click the calendar icon to open date picker
  const calendarIcon = input.locator('..').locator('[name="event"]');
  await calendarIcon.click();
  await page.waitForTimeout(500);

  // Set the date/time value directly via Vue
  await page.evaluate((value) => {
    if (window.app && window.app.formDialog && window.app.formDialog.data) {
      window.app.formDialog.data.end_datetime = value;
    }
  }, datetimeValue);

  // Close the picker by clicking outside
  await page.keyboard.press('Escape');
  await page.waitForTimeout(300);
}

(async () => {
  console.log('⏱️ Creating minutely allowance (2 sats per minute for 5 minutes)...');

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
    // Name - use the third input field which is for name
    const inputs = await page.locator('input[type="text"]').all();
    if (inputs.length >= 3) {
      await inputs[2].fill('Minutely Test - 2 sats for 5 minutes');
    }

    // Lightning address - use the fifth input field
    if (inputs.length >= 5) {
      await inputs[4].fill(config.payLinkEmail);
    }

    // Amount - 2 sats (keeping it simple, no currency conversion for now)
    await page.fill('input[type="number"]', '2');

    // Currency - keep as sats (default)

    // Frequency - select minutely
    const frequencySelect = page.locator('.q-select').filter({ hasText: 'Frequency' });
    await frequencySelect.click();
    await page.waitForTimeout(500);
    await page.click('.q-item:has-text("Minutely")');
    await page.waitForTimeout(500);
    console.log('✅ Selected minutely frequency');

    // Set end time to 5 minutes from now
    const now = new Date();
    const endTime = new Date(now.getTime() + 5 * 60 * 1000); // 5 minutes
    const endTimeStr = toQuasarDatetimeString(endTime);

    // Set end date & time using Quasar picker
    await setQuasarDatetime(page, 'End date & time', endTimeStr);

    // Memo - find the textarea
    const memoField = page.locator('textarea').first();
    if (await memoField.count() > 0) {
      await memoField.fill('Testing minutely payments: 2 sats every minute for 5 minutes');
    }

    console.log('📝 Form filled:');
    console.log('   Name: Minutely Test - 2 sats for 5 minutes');
    console.log('   Amount: 2 sats');
    console.log('   Frequency: minutely');
    console.log('   Duration: 5 minutes');
    console.log(`   End: ${endTime.toLocaleString()}`);

    // Submit the form - look for the Create button in the dialog
    await page.click('button[type="submit"]:has-text("Create")');
    await page.waitForTimeout(2000);

    // Check for success
    const cards = await page.locator('.q-card').count();
    if (cards > 0) {
      console.log('✅ Minutely allowance created successfully!');
      console.log('   Will send 2 sats every minute');
      console.log('   Total of 10 sats will be sent over 5 minutes');
    }

    // Take screenshot
    await page.screenshot({ path: 'test-screenshots/minutely-allowance-created.png' });
    console.log('📸 Screenshot saved: minutely-allowance-created.png');

  } catch (error) {
    console.error('❌ Failed to create minutely allowance:', error.message);
    await page.screenshot({ path: 'test-screenshots/minutely-allowance-error.png' });
    process.exit(1);
  } finally {
    await browser.close();
  }

  console.log('✅ Minutely allowance creation completed');
})();