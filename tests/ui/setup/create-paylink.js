#!/usr/bin/env node
/**
 * Create Paylink for Receiving Wallet
 * Creates a paylink with Lightning address from .env.local PAYLINK_EMAIL
 */

const { chromium } = require('playwright');
const { login, getConfig } = require('../auth-helper');

async function createPaylink() {
  const browser = await chromium.launch({
    headless: false,
    slowMo: 50
  });
  const context = await browser.newContext();
  const page = await context.newPage();
  const config = getConfig();
  const walletName = config.walletName || 'Receiving';
  const payLinkEmail = config.payLinkEmail;

  try {
    // Login first
    await login(page);
    console.log('✓ Logged in successfully');

    // Navigate to Pay Links extension at /lnurlp/
    await page.goto(`${config.baseUrl}/lnurlp/`);
    await page.waitForLoadState('networkidle');
    console.log('✓ Navigated to Pay Links extension');

    // Take screenshot
    await page.screenshot({ path: 'create-paylink-1-paylinks-page.png', fullPage: true });

    // Check if paylink already exists
    const existingPaylink = page.locator('tr').filter({ hasText: payLinkEmail });
    if (await existingPaylink.count() > 0) {
      console.log(`✓ Paylink for ${payLinkEmail} already exists`);

      // Get the Lightning address if visible
      const lnAddress = await existingPaylink.locator('td').nth(1).textContent();
      console.log(`✓ Lightning address: ${lnAddress}`);

      await page.screenshot({ path: 'create-paylink-2-already-exists.png', fullPage: true });
      await browser.close();
      return 0;
    }

    // Click New Pay Link button
    const createButton = page.locator('button:has-text("New Pay Link")').first();
    await createButton.click();
    console.log('✓ Clicked New Pay Link button');

    // Wait for dialog
    await page.waitForTimeout(2000);

    // Select the Receiving wallet from dropdown
    const walletDropdown = page.locator('select').first().or(page.locator('[role="combobox"]').first());
    if (await walletDropdown.isVisible()) {
      await walletDropdown.click();
      await page.waitForTimeout(500);
      const receivingOption = page.locator('[role="option"]').filter({ hasText: walletName }).first();
      if (await receivingOption.isVisible()) {
        await receivingOption.click();
        console.log(`✓ Selected ${walletName} wallet`);
      }
    }

    // Fill in the item description - look for the actual text input field for description
    const descriptionField = page.locator('input[aria-label="Item description *"]');
    await descriptionField.fill(`${walletName} Wallet Paylink`);
    console.log('✓ Set description');

    // The Lightning Address field already shows the domain, just need to set username part
    const lnAddressField = page.locator('input').filter({ hasText: '@' }).or(page.locator('input').nth(2));

    // Extract just the username part from the email
    const username = payLinkEmail.split('@')[0];
    if (await lnAddressField.isVisible()) {
      await lnAddressField.clear();
      await lnAddressField.fill(username);
      console.log(`✓ Set Lightning address username to: ${username}`);
    }

    // Uncheck "Fixed amount" to allow variable amounts
    const fixedAmountCheckbox = page.locator('.q-checkbox').first();
    const checkboxInput = fixedAmountCheckbox.locator('input[type="checkbox"]');
    const isChecked = await checkboxInput.isChecked();
    if (isChecked) {
      await fixedAmountCheckbox.click();
      console.log('✓ Unchecked fixed amount (variable amount enabled)');
      await page.waitForTimeout(1000);
    }

    // Set Min and Max amounts
    const numberInputs = await page.locator('input[type="number"]:visible').all();
    console.log(`Found ${numberInputs.length} number inputs`);

    if (numberInputs.length >= 2) {
      // Set Min amount
      await numberInputs[0].fill('1');
      console.log('✓ Set minimum amount: 1 sat');

      // Set Max amount
      await numberInputs[1].fill('99');
      console.log('✓ Set maximum amount: 99 sats');
    } else if (numberInputs.length === 1) {
      // If only one field, it's the Amount field for fixed amount
      await numberInputs[0].fill('10');
      console.log('✓ Set amount: 10 sats');
    }

    // Take screenshot of dialog
    await page.screenshot({ path: 'create-paylink-3-dialog.png', fullPage: true });

    // Click CREATE PAY LINK button
    const submitButton = page.locator('button:has-text("CREATE PAY LINK")');
    await submitButton.click();
    console.log('✓ Clicked CREATE PAY LINK button');

    // Wait for paylink to be created
    await page.waitForFunction(
      (email) => {
        const rows = document.querySelectorAll('tr');
        return Array.from(rows).some(row => row.textContent.includes(email));
      },
      payLinkEmail,
      { timeout: 10000 }
    );

    console.log(`✓ Paylink created successfully`);

    // Get the Lightning address
    await page.waitForTimeout(2000); // Wait for data to load
    const newPaylink = page.locator('tr').filter({ hasText: payLinkEmail }).first();
    if (await newPaylink.isVisible()) {
      const lnAddress = await newPaylink.locator('td').nth(1).textContent();
      console.log(`✓ Lightning address: ${lnAddress}`);
    }

    // Take final screenshot
    await page.screenshot({ path: 'create-paylink-4-created.png', fullPage: true });

    await browser.close();
    console.log(`✅ Paylink creation complete for ${payLinkEmail}`);
    return 0;

  } catch (error) {
    console.error('❌ Error creating paylink:', error);
    await page.screenshot({ path: 'create-paylink-error.png', fullPage: true });
    await browser.close();
    return 1;
  }
}

// Run the script
createPaylink().then(exitCode => {
  process.exit(exitCode);
});