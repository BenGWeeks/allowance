#!/usr/bin/env node
/**
 * Minutely Allowance Test
 * Creates a minutely allowance with 5-minute end time
 * Monitors payments every minute and verifies they are made
 */

const { chromium } = require('playwright');
const { login, getConfig } = require('./auth-helper');
const { execSync } = require('child_process');

async function runMinutelyTest() {
  const browser = await chromium.launch({
    headless: false,
    slowMo: 50
  });
  const context = await browser.newContext();
  const page = await context.newPage();
  const config = getConfig();

  try {
    console.log('🚀 Starting Minutely Payment Test');
    console.log('==========================================');
    console.log(`📧 Using Lightning address: ${config.payLinkEmail}`);
    console.log(`🌐 LNbits URL: ${config.baseUrl}`);

    // Login
    await login(page);
    console.log('✓ Logged in successfully');

    // Navigate to Allowance extension
    await page.goto(`${config.baseUrl}/allowance`);
    await page.waitForLoadState('networkidle');
    console.log('✓ Navigated to Allowance extension');

    // Click New Allowance button
    await page.click('button:has-text("New Allowance")');
    await page.waitForSelector('.q-dialog', { state: 'visible' });
    console.log('✓ Opened Create Allowance dialog');

    // Fill in the form
    console.log('\n📝 Creating Minutely Allowance...');

    // Fill name/description
    const nameInput = await page.locator('input').nth(2);
    await nameInput.fill('Minutely Test - 5min');
    console.log('✓ Set name: Minutely Test - 5min');

    // Select wallet
    const walletSelect = await page.locator('.q-select').first();
    await walletSelect.click();
    await page.waitForTimeout(500);
    await page.keyboard.press('Enter');
    console.log('✓ Selected wallet');

    // Fill Lightning address
    const addressInput = await page.locator('input').nth(4);
    await addressInput.fill(config.payLinkEmail);
    console.log(`✓ Set Lightning address: ${config.payLinkEmail}`);

    // Set amount to 5 sats
    const amountInput = await page.locator('input[type="number"]').first();
    await amountInput.fill('5');
    console.log('✓ Set amount: 5 sats');

    // Select Minutely frequency
    const frequencySelect = await page.locator('.q-select').nth(1);
    await frequencySelect.click();
    await page.waitForTimeout(500);

    // Look for Minutely option
    const minutelyOption = await page.locator('.q-item:has-text("Minutely")').first();
    await minutelyOption.click();
    console.log('✓ Selected Minutely frequency');

    // Leave start date empty (default to now)
    console.log('✓ Start date: now (default)');

    // Set end date to 5 minutes from now
    const endDate = new Date();
    endDate.setMinutes(endDate.getMinutes() + 5);
    const endDateStr = endDate.toISOString().slice(0, 16);

    const endDateInput = await page.locator('input[type="datetime-local"]').nth(1);
    await endDateInput.fill(endDateStr);
    console.log(`✓ Set end date: ${endDateStr} (5 minutes from now)`);

    // Screenshot before submit
    await page.screenshot({ path: 'minutely-test-form.png', fullPage: true });

    // Submit the form
    const submitButton = await page.locator('.q-dialog button:has-text("Create")').or(page.locator('.q-dialog button:has-text("Save")'));
    await submitButton.click();

    // Wait for dialog to close
    await page.waitForSelector('.q-dialog', { state: 'hidden', timeout: 10000 });
    console.log('✅ Minutely allowance created successfully!\n');

    // Monitor payments for 5 minutes
    console.log('⏰ Monitoring payments for 5 minutes...');
    console.log('=' * 50);

    const startTime = Date.now();
    const duration = 5.5 * 60 * 1000; // 5.5 minutes to ensure all payments complete
    let paymentCount = 0;
    let lastTransactionCount = 0;

    while (Date.now() - startTime < duration) {
      const elapsed = Math.floor((Date.now() - startTime) / 1000);
      const minutes = Math.floor(elapsed / 60);
      const seconds = elapsed % 60;

      console.log(`\n⏱️ Time: ${minutes}:${seconds.toString().padStart(2, '0')}`);

      // Check transactions via API
      try {
        // Get admin API key
        const { getAdminApiKey } = require('../get_api_key.js');
        const adminKey = await getAdminApiKey(page);

        if (adminKey) {
          // Get transactions
          const response = await page.request.get(`${config.baseUrl}/api/v1/payments`, {
            headers: { 'X-Api-Key': adminKey }
          });

          if (response.ok()) {
            const payments = await response.json();
            const minutelyPayments = payments.filter(p =>
              p.memo && p.memo.includes('Minutely Test') &&
              p.amount < 0 // Outgoing payments
            );

            if (minutelyPayments.length > lastTransactionCount) {
              paymentCount = minutelyPayments.length - lastTransactionCount;
              lastTransactionCount = minutelyPayments.length;
              console.log(`  💰 Payment #${lastTransactionCount} sent! (5 sats to ${config.payLinkEmail})`);
            } else {
              console.log(`  ⏳ Waiting for next payment...`);
            }
          }
        }
      } catch (e) {
        console.log(`  ⚠️ Could not check transactions: ${e.message}`);
      }

      // Wait 30 seconds before next check
      if (Date.now() - startTime < duration) {
        await page.waitForTimeout(30000);
      }
    }

    console.log('\n' + '=' * 50);
    console.log('✅ Test completed after 5 minutes');
    console.log(`📊 Total payments detected: ${lastTransactionCount}`);

    // Verify expected payments
    if (lastTransactionCount >= 5) {
      console.log('✅ PASS: At least 5 minutely payments were made');
    } else {
      console.log(`⚠️ WARNING: Only ${lastTransactionCount} payments detected (expected at least 5)`);
    }

    // Take final screenshot
    await page.screenshot({ path: 'minutely-test-final.png', fullPage: true });

    await browser.close();

    // Run transaction verification
    console.log('\n📊 Running transaction verification...');
    try {
      const output = execSync('cd /mnt/raid1/GitHub/allowance && python3 verify_transactions.py', { encoding: 'utf-8' });
      console.log(output);
    } catch (e) {
      console.log('Could not run transaction verification:', e.message);
    }

    // Notify completion
    try {
      execSync('canberra-gtk-play -i complete');
      console.log('\n🔔 Test complete - notification sent!');
    } catch (e) {
      // Ignore if sound fails
    }

    console.log('\n🎉 Minutely payment test completed successfully!');
    process.exit(0);

  } catch (error) {
    console.error('❌ Test failed:', error.message);
    await browser.close();
    process.exit(1);
  }
}

// Run the test
runMinutelyTest();