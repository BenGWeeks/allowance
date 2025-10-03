const { chromium } = require('playwright');
const { login, getConfig } = require('../auth-helper');

async function installAllowanceExtension() {
  const config = getConfig();
  const browser = await chromium.launch({ headless: false });
  const page = await browser.newPage();

  try {
    console.log('🔌 Installing Allowance extension...');

    // Login first
    await login(page);

    // Navigate to Extensions
    console.log('📝 Navigating to Extensions...');

    // Look for Extensions menu more specifically
    const extensionsSelectors = [
      '[data-cy="extensions"]',
      '.q-item:has(.q-item__label:has-text("Extensions"))',
      'a[href="/extensions"]',
      'text=Extensions'
    ];

    let extensionsFound = false;
    for (const selector of extensionsSelectors) {
      try {
        if (await page.locator(selector).first().isVisible({ timeout: 3000 })) {
          console.log(`✅ Found Extensions using selector: ${selector}`);
          await page.locator(selector).first().click();
          await page.waitForTimeout(2000);
          extensionsFound = true;
          break;
        }
      } catch (error) {
        // Continue to next selector
      }
    }

    if (!extensionsFound) {
      // Try direct navigation
      console.log('📝 Trying direct navigation to /extensions...');
      await page.goto(config.baseUrl + '/extensions');
      await page.waitForTimeout(2000);
    }

    await page.screenshot({ path: 'tests/test-results/install-extensions-page.png', fullPage: true });
    console.log('📷 Extensions page: install-extensions-page.png');

    // Check if Allowance extension is already visible
    const allowanceVisible = await page.locator('text=Allowance').isVisible();

    if (allowanceVisible) {
      console.log('✅ Allowance extension is already visible');

      // Look more specifically for the Enable button in the Allowance card
      const allowanceCard = page.locator('.q-card:has-text("Allowance")');
      const enableButton = allowanceCard.locator('button:has-text("Enable")');
      const disableButton = allowanceCard.locator('button:has-text("Disable")');

      if (await enableButton.isVisible()) {
        console.log('📝 Enabling Allowance extension...');
        await enableButton.click();
        await page.waitForTimeout(3000);
        console.log('✅ Allowance extension enabled');

        // Verify it was enabled by checking for Disable button
        if (await disableButton.isVisible()) {
          console.log('✅ Extension enable confirmed - Disable button now visible');
        }
      } else if (await disableButton.isVisible()) {
        console.log('✅ Allowance extension is already enabled');
      } else {
        console.log('⚠️ Could not find Enable or Disable button for Allowance extension');
        await page.screenshot({ path: 'tests/test-results/install-allowance-buttons.png', fullPage: true });
        console.log('📷 Button debug screenshot: install-allowance-buttons.png');
      }

    } else {
      console.log('📝 Allowance extension not found, need to install it...');

      // Look for "Add extension" or similar button
      const addExtensionSelectors = [
        'button:has-text("Add Extension")',
        'button:has-text("Install Extension")',
        'button:has-text("+")',
        '[data-cy="add-extension"]'
      ];

      let addButtonFound = false;
      for (const selector of addExtensionSelectors) {
        try {
          if (await page.locator(selector).isVisible({ timeout: 2000 })) {
            console.log(`📝 Clicking add extension button: ${selector}`);
            await page.click(selector);
            await page.waitForTimeout(2000);
            addButtonFound = true;
            break;
          }
        } catch (error) {
          // Continue to next selector
        }
      }

      if (addButtonFound) {
        console.log('📝 Looking for Allowance in extension list...');
        await page.screenshot({ path: 'tests/test-results/install-extension-list.png', fullPage: true });
        console.log('📷 Extension list: install-extension-list.png');

        // Try to find and install Allowance
        const allowanceExtension = page.locator('.q-card:has-text("Allowance")');
        if (await allowanceExtension.isVisible()) {
          console.log('📝 Found Allowance extension, installing...');
          const installButton = allowanceExtension.locator('button:has-text("Install")');
          if (await installButton.isVisible()) {
            await installButton.click();
            await page.waitForTimeout(3000);
            console.log('✅ Allowance extension installed');
          }
        }
      }
    }

    // Final verification
    await page.screenshot({ path: 'tests/test-results/install-final-state.png', fullPage: true });
    console.log('📷 Final state: install-final-state.png');

    // Try to navigate to the Allowance extension
    console.log('📝 Testing access to Allowance extension...');
    await page.goto(config.baseUrl + '/extensions/allowance');
    await page.waitForTimeout(3000);

    const currentUrl = page.url();
    const bodyText = await page.locator('body').textContent();

    if (currentUrl.includes('/extensions/allowance') && !bodyText.includes('404')) {
      console.log('✅ Allowance extension is accessible');

      await page.screenshot({ path: 'tests/test-results/install-allowance-working.png', fullPage: true });
      console.log('📷 Working extension: install-allowance-working.png');

    } else {
      console.log('❌ Allowance extension not accessible');
      console.log('   Current URL:', currentUrl);
    }

  } catch (error) {
    console.error('❌ Error installing extension:', error.message);
    await page.screenshot({ path: 'tests/test-results/install-error.png', fullPage: true });
    console.log('📷 Error screenshot: install-error.png');
  }

  await browser.close();
}

installAllowanceExtension().catch(console.error);