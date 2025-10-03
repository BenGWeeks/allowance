const { chromium } = require('playwright');
const { login, getConfig } = require('../auth-helper');

async function enablePaylinks() {
  const config = getConfig();
  const browser = await chromium.launch({ headless: false });
  const page = await browser.newPage();

  try {
    console.log('🔍 Enabling Pay Links extension...');

    // Login first
    await login(page);

    // Navigate to extensions page
    console.log('📝 Navigating to extensions page...');
    await page.goto(`${config.baseUrl}/extensions`);
    await page.waitForTimeout(2000);

    // Look for Pay Links extension card (note the space in "Pay Links")
    console.log('📝 Looking for Pay Links extension...');

    // Check if Pay Links is already enabled
    const paylinkCard = page.locator('.q-card:has(.text-h5:has-text("Pay Links"))');

    if (await paylinkCard.isVisible()) {
      // Check if it has a Disable button (meaning it's enabled)
      const disableButton = paylinkCard.locator('button:has-text("Disable")');
      if (await disableButton.isVisible()) {
        console.log('✅ Pay Links extension is already enabled');
        return true;
      }

      // Look for Enable button
      const enableButton = paylinkCard.locator('button:has-text("Enable")');
      if (await enableButton.isVisible()) {
        console.log('📝 Clicking Enable button for Pay Links...');
        await enableButton.click();
        await page.waitForTimeout(3000);

        // Verify it's enabled
        const nowDisableButton = paylinkCard.locator('button:has-text("Disable")');
        if (await nowDisableButton.isVisible()) {
          console.log('✅ Pay Links extension enabled successfully');
          return true;
        } else {
          console.log('❌ Failed to enable Pay Links extension');
          return false;
        }
      }
    } else {
      console.log('❌ Pay Links extension not found');
      await page.screenshot({ path: 'tests/test-results/test-paylinks-not-found.png', fullPage: true });
      return false;
    }

  } catch (error) {
    console.error('❌ Error enabling Pay Links:', error.message);
    await page.screenshot({ path: 'tests/test-results/test-paylinks-error.png', fullPage: true });
    return false;
  } finally {
    await browser.close();
  }
}

enablePaylinks()
  .then(success => {
    console.log('Result:', success ? 'PASS' : 'FAIL');
    process.exit(success ? 0 : 1);
  })
  .catch(error => {
    console.error('Test failed:', error.message);
    process.exit(1);
  });