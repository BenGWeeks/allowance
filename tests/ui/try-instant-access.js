const { chromium } = require('playwright');
const { getConfig } = require('./auth-helper');

async function tryInstantAccess() {
  const config = getConfig();
  const browser = await chromium.launch({ headless: false });
  const page = await browser.newPage();

  try {
    console.log('🔌 Testing instant access to LNBits...');

    await page.goto(config.baseUrl);
    await page.waitForLoadState('networkidle');

    console.log('✅ Page loaded:', page.url());

    // Take screenshot of initial state
    await page.screenshot({ path: 'instant-access-initial.png', fullPage: true });
    console.log('📷 Initial screenshot: instant-access-initial.png');

    // Try clicking "Create New Wallet" button
    const createWalletButton = page.locator('button:has-text("Create New Wallet")');

    if (await createWalletButton.isVisible()) {
      console.log('📝 Clicking "Create New Wallet"...');
      await createWalletButton.click();
      await page.waitForTimeout(3000);

      await page.screenshot({ path: 'instant-access-after-create.png', fullPage: true });
      console.log('📷 After create wallet: instant-access-after-create.png');

      // Check if we're now in the wallet interface
      const bodyText = await page.locator('body').textContent();

      if (bodyText.includes('Extensions') || bodyText.includes('Wallet') || bodyText.includes('Add a new wallet')) {
        console.log('✅ Successfully accessed LNBits wallet interface');

        // Try to access extensions
        console.log('🔌 Looking for Extensions menu...');

        // Look for various ways to access extensions
        const extensionsSelectors = [
          'text=Extensions',
          '[data-cy="extensions"]',
          'button:has-text("Extensions")',
          'a:has-text("Extensions")',
          '.q-item:has-text("Extensions")'
        ];

        let extensionsFound = false;
        for (const selector of extensionsSelectors) {
          if (await page.locator(selector).isVisible()) {
            console.log(`✅ Found Extensions using selector: ${selector}`);
            await page.click(selector);
            await page.waitForTimeout(2000);
            extensionsFound = true;
            break;
          }
        }

        if (extensionsFound) {
          await page.screenshot({ path: 'instant-access-extensions.png', fullPage: true });
          console.log('📷 Extensions page: instant-access-extensions.png');

          // Check if Allowance extension is visible
          const allowanceVisible = await page.locator('text=Allowance').isVisible();
          console.log('🔍 Allowance extension visible:', allowanceVisible);

        } else {
          console.log('❌ Could not find Extensions menu');
        }

      } else {
        console.log('❌ Did not reach wallet interface');
        console.log('🔍 Body contains:', bodyText.substring(0, 200));
      }

    } else {
      console.log('❌ "Create New Wallet" button not found');
    }

  } catch (error) {
    console.error('❌ Error:', error.message);
    await page.screenshot({ path: 'instant-access-error.png', fullPage: true });
    console.log('📷 Error screenshot: instant-access-error.png');
  }

  await browser.close();
}

tryInstantAccess().catch(console.error);