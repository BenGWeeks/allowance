#!/usr/bin/env node

const { chromium } = require('playwright');
const { getConfig, login } = require('./auth-helper');

(async () => {
  console.log('📋 Listing all allowances...');

  const config = getConfig();
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();

  try {
    // Login
    await login(page);
    console.log('✅ Logged in successfully');

    // Navigate to allowance extension
    await page.goto(`${config.baseUrl}/allowance`);
    await page.waitForTimeout(3000);
    console.log('✅ Navigated to allowance extension');

    // Find all table rows with allowance names
    const rows = await page.locator('tbody tr').all();
    console.log(`\n📊 Found ${rows.length} allowances:\n`);

    for (let i = 0; i < rows.length; i++) {
      const nameCell = await rows[i].locator('td').first().textContent();
      console.log(`  ${i + 1}. ${nameCell?.trim()}`);
    }

    // Also try to get the data from Vue app
    const allowances = await page.evaluate(() => {
      if (window.app && window.app.allowances) {
        return window.app.allowances.map(a => ({
          id: a.id,
          name: a.name,
          amount: a.amount,
          currency: a.currency,
          frequency_type: a.frequency_type,
          active: a.active
        }));
      }
      return [];
    });

    if (allowances.length > 0) {
      console.log('\n📝 Detailed allowance data from Vue:');
      allowances.forEach((a, i) => {
        console.log(`\n  ${i + 1}. ${a.name}`);
        console.log(`     ID: ${a.id}`);
        console.log(`     Amount: ${a.amount} ${a.currency}`);
        console.log(`     Frequency: ${a.frequency_type}`);
        console.log(`     Active: ${a.active}`);
      });
    }

  } catch (error) {
    console.error('❌ Failed to list allowances:', error.message);
    process.exit(1);
  } finally {
    await browser.close();
  }

  console.log('\n✅ Listing completed');
})();