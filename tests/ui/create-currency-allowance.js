#!/usr/bin/env node

const { chromium } = require('playwright');
const { getConfig, login } = require('./auth-helper');

(async () => {
  console.log('🌍 Testing scheduled payments with currency conversion (GBP)...');

  const config = getConfig();
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();

  try {
    // Login
    await login(page);
    console.log('✅ Logged in successfully');

    // Navigate to allowance extension
    await page.goto(`${config.baseUrl}/extensions?usr=${config.userId}`);
    await page.waitForTimeout(2000);

    // Find and click on allowance extension
    const allowanceCard = page.locator('.q-card').filter({ hasText: 'allowance' }).first();
    await allowanceCard.click();
    await page.waitForTimeout(2000);
    console.log('✅ Navigated to allowance extension');

    // Create new allowance with GBP currency
    const allowanceData = {
      name: `GBP Test ${Date.now()}`,
      lightning_address: config.payLinkEmail || 'test@example.com',
      amount: 0.02,  // £0.02 GBP
      currency: 'GBP',
      frequency_type: 'minutely',
      memo: 'Testing GBP conversion to sats'
    };

    // Make API call to create allowance
    const apiKey = config.adminApiKey || await page.locator('[data-api-key]').first().getAttribute('data-api-key');

    const response = await fetch(`${config.baseUrl}/allowance/api/v1/allowances`, {
      method: 'POST',
      headers: {
        'X-Api-Key': apiKey,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(allowanceData)
    });

    if (!response.ok) {
      throw new Error(`Failed to create allowance: ${response.statusText}`);
    }

    const created = await response.json();
    console.log(`✅ Created GBP allowance: ${created.name}`);
    console.log(`   Amount: £${allowanceData.amount} GBP`);
    console.log(`   Will be converted to sats at current rate`);
    console.log(`   ID: ${created.id}`);

    // Wait a minute to see if payment is triggered
    console.log('⏳ Waiting 65 seconds for first scheduled payment...');
    await page.waitForTimeout(65000);

    // Check if payment was made (would need to check wallet balance or payment history)
    console.log('ℹ️  Check the wallet to verify GBP was converted to sats and paid');

    // Clean up - delete the test allowance
    const deleteResponse = await fetch(`${config.baseUrl}/allowance/api/v1/allowances/${created.id}`, {
      method: 'DELETE',
      headers: {
        'X-Api-Key': apiKey
      }
    });

    if (deleteResponse.ok) {
      console.log('✅ Test allowance deleted');
    }

  } catch (error) {
    console.error('❌ Test failed:', error.message);
    process.exit(1);
  } finally {
    await browser.close();
  }

  console.log('✅ Currency scheduled payment test completed');
})();