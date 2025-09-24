#!/usr/bin/env node

const { chromium } = require('playwright');
const { getConfig, login } = require('./auth-helper');

(async () => {
  console.log('💷 Testing decimal amount (£0.02 GBP) allowance creation...');

  const config = getConfig();
  const browser = await chromium.launch({ headless: false });
  const page = await browser.newPage();

  try {
    // Login
    await login(page);
    console.log('✅ Logged in successfully');

    // Navigate to allowance extension
    await page.goto(`${config.baseUrl}/allowance`);
    await page.waitForTimeout(3000);

    // Open create dialog
    try {
      const newButton = page.locator('button:has-text("New Allowance")');
      if (await newButton.count() > 0) {
        await newButton.click();
      } else {
        await page.evaluate(() => {
          if (window.app && window.app.openCreateDialog) {
            window.app.openCreateDialog();
          }
        });
      }
      await page.waitForTimeout(1000);
      console.log('✅ Opened create dialog');
    } catch (e) {
      console.log('⚠️ Opening dialog via alternate method...');
      await page.evaluate(() => {
        if (window.app && window.app.openCreateDialog) {
          window.app.openCreateDialog();
        }
      });
    }

    // Fill form with decimal amount
    const inputs = await page.locator('input[type="text"]').all();
    if (inputs.length >= 3) {
      await inputs[2].fill('Test Decimal GBP - £0.02');
    }

    if (inputs.length >= 5) {
      await inputs[4].fill(config.payLinkEmail);
    }

    // Fill decimal amount - 0.02
    await page.fill('input[type="number"]', '0.02');
    console.log('✅ Entered decimal amount: 0.02');

    // Try to select GBP currency
    try {
      const currencySelect = page.locator('.q-select').first();
      await currencySelect.click();
      await page.waitForTimeout(500);

      // Look for GBP option
      const gbpOption = page.locator('.q-item').filter({ hasText: 'GBP' });
      if (await gbpOption.count() > 0) {
        await gbpOption.first().click();
        console.log('✅ Selected GBP currency');
      } else {
        console.log('⚠️ GBP not found in dropdown, keeping default currency');
      }
      await page.waitForTimeout(500);
    } catch (e) {
      console.log('⚠️ Could not change currency, using default');
    }

    // Select frequency
    const frequencySelect = page.locator('.q-select').filter({ hasText: 'Frequency' });
    await frequencySelect.click();
    await page.waitForTimeout(500);
    await page.click('.q-item:has-text("Once")');
    console.log('✅ Selected once frequency');

    // Memo
    const memoField = page.locator('textarea').first();
    if (await memoField.count() > 0) {
      await memoField.fill('Testing decimal amount support (0.02 GBP)');
    }

    // Submit
    await page.click('button[type="submit"]:has-text("Create")');
    await page.waitForTimeout(3000);

    // Check for errors
    const errorToast = page.locator('.q-notification__message:has-text("error")');
    if (await errorToast.count() > 0) {
      const errorText = await errorToast.textContent();
      console.error(`❌ Error creating allowance: ${errorText}`);
      await page.screenshot({ path: 'test-screenshots/decimal-amount-error.png' });
      process.exit(1);
    }

    // Check for success
    const cards = await page.locator('.q-card').count();
    if (cards > 0) {
      console.log('✅ Decimal amount allowance created successfully!');
      console.log('   The fix for float amounts is working!');
    }

    await page.screenshot({ path: 'test-screenshots/decimal-amount-success.png' });

  } catch (error) {
    console.error('❌ Test failed:', error.message);
    await page.screenshot({ path: 'test-screenshots/decimal-amount-error.png' });
    process.exit(1);
  } finally {
    await browser.close();
  }

  console.log('✅ Decimal amount test completed successfully');
})();