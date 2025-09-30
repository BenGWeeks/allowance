#!/usr/bin/env node
/**
 * Install Allowance Extension
 * Installs the Allowance extension for LNBits
 */

const { chromium } = require('playwright');
const { login, getConfig } = require('../auth-helper');

async function installAllowanceExtension() {
  const browser = await chromium.launch({
    headless: false,
    slowMo: 50
  });
  const context = await browser.newContext();
  const page = await context.newPage();
  const config = getConfig();

  try {
    // Login first
    await login(page);
    console.log('✓ Logged in successfully');

    // Navigate to extensions page
    await page.goto(`${config.baseUrl}/extensions`);
    await page.waitForLoadState('networkidle');
    console.log('✓ Navigated to extensions page');

    // Take screenshot
    await page.screenshot({ path: 'install-allowance-1-extensions-page.png', fullPage: true });

    // Search for Allowance extension
    await page.fill('input[aria-label="Search"]', 'allowance');
    await page.waitForTimeout(1000); // Wait for search results to filter
    console.log('✓ Searched for Allowance extension');

    // Take screenshot after search
    await page.screenshot({ path: 'install-allowance-2-search-results.png', fullPage: true });

    // Find the Allowance extension card
    const allowanceCard = page.locator('.q-card').filter({ hasText: 'Allowance' }).first();

    // Check if already installed by looking for "Uninstall" button
    const uninstallButton = allowanceCard.locator('button:has-text("Uninstall")');
    const installButton = allowanceCard.locator('button:has-text("Install")');

    if (await uninstallButton.isVisible()) {
      console.log('✓ Allowance extension is already installed');
      await page.screenshot({ path: 'install-allowance-3-already-installed.png', fullPage: true });
      await browser.close();
      return 0;
    }

    // Click Install button if not installed
    if (await installButton.isVisible()) {
      await installButton.click();
      console.log('✓ Clicked Install button');

      // Wait for installation to complete (button changes to Uninstall)
      await page.waitForFunction(
        () => {
          const card = document.querySelector('.q-card:has(.text-h5:has-text("Allowance"))');
          if (!card) return false;
          const uninstallBtn = card.querySelector('button:has-text("Uninstall")');
          return uninstallBtn !== null;
        },
        { timeout: 30000 }
      );

      console.log('✓ Allowance extension installed successfully');
      await page.screenshot({ path: 'install-allowance-4-installed.png', fullPage: true });
    } else {
      throw new Error('Could not find Install or Uninstall button for Allowance');
    }

    await browser.close();
    console.log('✅ Allowance extension installation complete');
    return 0;

  } catch (error) {
    console.error('❌ Error installing Allowance extension:', error);
    await page.screenshot({ path: 'install-allowance-error.png', fullPage: true });
    await browser.close();
    return 1;
  }
}

// Run the script
installAllowanceExtension().then(exitCode => {
  process.exit(exitCode);
});