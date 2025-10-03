#!/usr/bin/env node
/**
 * Install Paylinks Extension
 * Installs the Paylinks extension for LNBits
 */

const { chromium } = require('playwright');
const { login, getConfig } = require('../auth-helper');

async function installPaylinkExtension() {
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
    await page.screenshot({ path: 'tests/test-results/install-paylinks-1-extensions-page.png', fullPage: true });

    // Search for Paylinks extension
    await page.fill('input[aria-label="Search"]', 'paylinks');
    await page.waitForTimeout(1000); // Wait for search results to filter
    console.log('✓ Searched for Paylinks extension');

    // Take screenshot after search
    await page.screenshot({ path: 'tests/test-results/install-paylinks-2-search-results.png', fullPage: true });

    // Find the Paylinks extension card
    const paylinkCard = page.locator('.q-card').filter({ hasText: 'Paylinks' }).first();

    // Check if already installed by looking for "Uninstall" button
    const uninstallButton = paylinkCard.locator('button:has-text("Uninstall")');
    const installButton = paylinkCard.locator('button:has-text("Install")');

    if (await uninstallButton.isVisible()) {
      console.log('✓ Paylinks extension is already installed');
      await page.screenshot({ path: 'tests/test-results/install-paylinks-3-already-installed.png', fullPage: true });
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
          const card = document.querySelector('.q-card:has(.text-h5:has-text("Paylinks"))');
          if (!card) return false;
          const uninstallBtn = card.querySelector('button:has-text("Uninstall")');
          return uninstallBtn !== null;
        },
        { timeout: 30000 }
      );

      console.log('✓ Paylinks extension installed successfully');
      await page.screenshot({ path: 'tests/test-results/install-paylinks-4-installed.png', fullPage: true });
    } else {
      throw new Error('Could not find Install or Uninstall button for Paylinks');
    }

    await browser.close();
    console.log('✅ Paylinks extension installation complete');
    return 0;

  } catch (error) {
    console.error('❌ Error installing Paylinks extension:', error);
    await page.screenshot({ path: 'tests/test-results/install-paylinks-error.png', fullPage: true });
    await browser.close();
    return 1;
  }
}

// Run the script
installPaylinkExtension().then(exitCode => {
  process.exit(exitCode);
});