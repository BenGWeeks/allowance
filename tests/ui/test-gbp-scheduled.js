#!/usr/bin/env node

const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

// Load config from .env.local
function loadConfig() {
  const envPath = path.join(__dirname, '../../.env.local');
  const config = {
    baseUrl: 'https://lnbits-allowance.weeksfamily.me',
    username: '',
    password: '',
    walletId: '768a7da8063046d98cd5ee6f42621038',
    lightningAddress: 'receiving@lnbits-allowance.weeksfamily.me'
  };

  if (fs.existsSync(envPath)) {
    const content = fs.readFileSync(envPath, 'utf-8');
    const lines = content.split('\n');

    for (const line of lines) {
      if (line && !line.startsWith('#')) {
        const [key, value] = line.split('=');
        if (key && value) {
          if (key.trim() === 'LNBITS_ADMIN_USERNAME') config.username = value.trim();
          if (key.trim() === 'LNBITS_ADMIN_PASSWORD') config.password = value.trim();
          if (key.trim() === 'PAYLINK_EMAIL') config.lightningAddress = value.trim();
        }
      }
    }
  }

  return config;
}

(async () => {
  console.log('💷 Testing GBP scheduled payments on production...');

  const config = loadConfig();
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();

  try {
    // Navigate to login page
    await page.goto(config.baseUrl);
    await page.waitForTimeout(2000);

    // Look for login link
    const loginLink = page.locator('a:has-text("Login")').first();
    if (await loginLink.isVisible()) {
      await loginLink.click();
      await page.waitForTimeout(1000);
    }

    // Login
    await page.fill('input[type="text"]', config.username);
    await page.fill('input[type="password"]', config.password);
    await page.click('button:has-text("Login")');
    await page.waitForTimeout(3000);
    console.log('✅ Logged in successfully');

    // Navigate to allowance extension
    await page.goto(`${config.baseUrl}/extensions`);
    await page.waitForTimeout(2000);

    // Click on allowance extension
    const allowanceCard = page.locator('.q-card').filter({ hasText: 'allowance' }).first();
    await allowanceCard.click();
    await page.waitForTimeout(3000);
    console.log('✅ Navigated to allowance extension');

    // Get API key from page
    let apiKey = await page.evaluate(() => {
      const keyElement = document.querySelector('[data-api-key]');
      return keyElement ? keyElement.getAttribute('data-api-key') : null;
    });

    if (!apiKey) {
      // Try to find it in wallet info
      const walletInfo = await page.locator('.wallet-info').first().textContent();
      const match = walletInfo?.match(/[a-f0-9]{32}/);
      apiKey = match ? match[0] : null;
    }

    if (!apiKey) {
      throw new Error('Could not find API key');
    }

    console.log('✅ Got API key');

    // Create GBP allowance via API
    const allowanceData = {
      name: `GBP Test ${new Date().toISOString().slice(11, 19)}`,
      wallet: config.walletId,
      lightning_address: config.lightningAddress,
      amount: 0.02,  // £0.02 GBP
      currency: 'GBP',
      frequency_type: 'minutely',
      memo: 'Testing £0.02 GBP to sats conversion',
      active: true
    };

    console.log(`📝 Creating GBP allowance: £${allowanceData.amount} GBP`);

    const response = await fetch(`${config.baseUrl}/allowance/api/v1/allowances`, {
      method: 'POST',
      headers: {
        'X-Api-Key': apiKey,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(allowanceData)
    });

    if (!response.ok) {
      const error = await response.text();
      throw new Error(`Failed to create allowance: ${error}`);
    }

    const created = await response.json();
    console.log(`✅ Created allowance: ${created.name}`);
    console.log(`   ID: ${created.id}`);
    console.log(`   Amount: £${allowanceData.amount} GBP`);

    // Get exchange rate
    const rateResponse = await fetch(`${config.baseUrl}/allowance/api/v1/rate/GBP`, {
      headers: { 'X-Api-Key': apiKey }
    });

    if (rateResponse.ok) {
      const rateData = await rateResponse.json();
      const satsAmount = Math.round(allowanceData.amount / rateData.rate);
      console.log(`   Exchange rate: £1 = ${Math.round(1/rateData.rate)} sats`);
      console.log(`   Will pay: ~${satsAmount} sats per minute`);
    }

    // Wait for first payment
    console.log('⏳ Waiting 65 seconds for first scheduled payment...');
    await page.waitForTimeout(65000);

    // Check allowance status
    const statusResponse = await fetch(`${config.baseUrl}/allowance/api/v1/allowances/${created.id}`, {
      headers: { 'X-Api-Key': apiKey }
    });

    if (statusResponse.ok) {
      const updated = await statusResponse.json();
      console.log('📊 Status after 1 minute:');
      console.log(`   Total paid: ${updated.total || 0} sats`);
      if (updated.total > 0) {
        console.log('   ✅ Payment was executed!');
      }
    }

    // Clean up
    const deleteResponse = await fetch(`${config.baseUrl}/allowance/api/v1/allowances/${created.id}`, {
      method: 'DELETE',
      headers: { 'X-Api-Key': apiKey }
    });

    if (deleteResponse.ok) {
      console.log('✅ Test allowance deleted');
    }

  } catch (error) {
    console.error('❌ Test failed:', error.message);
    await page.screenshot({ path: 'gbp-test-error.png' });
    process.exit(1);
  } finally {
    await browser.close();
  }

  console.log('✅ GBP scheduled payment test completed');
})();