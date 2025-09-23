#!/usr/bin/env node

const { chromium } = require('playwright');
const { getConfig, login } = require('./auth-helper');

(async () => {
  console.log('⏰ Creating hourly allowance (2 sats/hour for 3 hours)...');

  const config = getConfig();
  const browser = await chromium.launch({ headless: false });
  const page = await browser.newPage();

  try {
    // Login
    await login(page);
    console.log('✅ Logged in successfully');

    // Navigate to allowance extension
    await page.goto(`${config.baseUrl}/extensions`);
    await page.waitForTimeout(2000);

    // Click on allowance extension
    const allowanceCard = page.locator('.q-card').filter({ hasText: 'allowance' }).first();
    await allowanceCard.click();
    await page.waitForTimeout(2000);
    console.log('✅ Navigated to allowance extension');

    // Click Create Allowance button
    await page.click('button:has-text("Create Allowance")');
    await page.waitForTimeout(1000);

    // Fill in the form
    const now = new Date();
    const endTime = new Date(now.getTime() + 3 * 60 * 60 * 1000); // 3 hours from now

    // Name
    await page.fill('input[aria-label="Name"]', 'Hourly Test - 2 sats for 3 hours');

    // Lightning address
    await page.fill('input[aria-label="Lightning address"]', config.payLinkEmail || 'receiving@lnbits-allowance.weeksfamily.me');

    // Amount - 2 sats
    await page.fill('input[aria-label="Amount"]', '2');

    // Currency - keep as sats (default)

    // Frequency - select hourly
    await page.click('input[aria-label="Frequency"]');
    await page.waitForTimeout(500);
    await page.click('.q-item:has-text("hourly")');
    await page.waitForTimeout(500);

    // Start date & time (optional - will use current time)
    const startDateInput = page.locator('input[aria-label="Start date & time (optional)"]');
    if (await startDateInput.isVisible()) {
      await startDateInput.fill(now.toISOString().slice(0, 16));
    }

    // End date & time - set to 3 hours from now
    const endDateInput = page.locator('input[aria-label="End date & time (optional)"]');
    if (await endDateInput.isVisible()) {
      await endDateInput.fill(endTime.toISOString().slice(0, 16));
    }

    // Memo
    await page.fill('textarea[aria-label="Memo"]', 'Testing hourly payments: 2 sats every hour for 3 hours');

    // Active checkbox - should be checked by default
    const activeCheckbox = page.locator('input[type="checkbox"]').first();
    const isChecked = await activeCheckbox.isChecked();
    if (!isChecked) {
      await activeCheckbox.click();
    }

    console.log('📝 Form filled:');
    console.log('   Name: Hourly Test - 2 sats for 3 hours');
    console.log('   Amount: 2 sats');
    console.log('   Frequency: hourly');
    console.log('   Duration: 3 hours');
    console.log(`   Start: ${now.toLocaleString()}`);
    console.log(`   End: ${endTime.toLocaleString()}`);

    // Submit the form
    await page.click('button:has-text("Create Allowance")');
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
    await page.screenshot({ path: 'hourly-allowance-created.png' });
    console.log('📸 Screenshot saved: hourly-allowance-created.png');

  } catch (error) {
    console.error('❌ Failed to create hourly allowance:', error.message);
    await page.screenshot({ path: 'hourly-allowance-error.png' });
    process.exit(1);
  } finally {
    await browser.close();
  }

  console.log('✅ Hourly allowance creation completed');
  console.log('ℹ️  Monitor the allowance to verify payments are sent hourly');
})();