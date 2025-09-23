const { chromium } = require('playwright');
const { getConfig } = require('./auth-helper');

async function createAccount() {
  const config = getConfig();
  const browser = await chromium.launch({ headless: false });
  const page = await browser.newPage();

  try {
    console.log('🔌 Creating new account on LNBits...');

    await page.goto(config.baseUrl);
    await page.waitForLoadState('networkidle');

    console.log('✅ Page loaded:', page.url());

    // Take screenshot of initial state
    await page.screenshot({ path: 'create-account-initial.png', fullPage: true });
    console.log('📷 Initial screenshot: create-account-initial.png');

    // Fill in the create account form
    console.log('📝 Filling account creation form...');

    // Fill username field (look for the first text input)
    const usernameField = page.locator('input[type="text"]:first-of-type, input:not([type="password"]):first-of-type');
    await usernameField.click();
    await usernameField.fill(config.username);
    await page.waitForTimeout(500);
    console.log('✅ Username filled');

    // Fill password field using aria-label
    const passwordField = page.locator('input[aria-label="Password *"]');
    await passwordField.click();
    await passwordField.fill(config.password);
    await page.waitForTimeout(500);
    console.log('✅ Password filled');

    // Fill password repeat field using aria-label
    const passwordRepeatField = page.locator('input[aria-label="Password repeat *"]');
    await passwordRepeatField.click();
    await passwordRepeatField.fill(config.password);
    await page.waitForTimeout(500);
    console.log('✅ Password repeat filled');

    // Wait for form validation
    await page.waitForTimeout(1000);

    await page.screenshot({ path: 'create-account-filled.png', fullPage: true });
    console.log('📷 Form filled: create-account-filled.png');

    // Click CREATE ACCOUNT button
    console.log('📝 Clicking CREATE ACCOUNT button...');
    await page.click('button:has-text("CREATE ACCOUNT")');
    await page.waitForTimeout(5000);

    await page.screenshot({ path: 'create-account-after-submit.png', fullPage: true });
    console.log('📷 After account creation: create-account-after-submit.png');

    // Check current state
    console.log('\n🔍 Post-creation state:');
    console.log('   Current URL:', page.url());
    console.log('   Page title:', await page.title());

    // Check for success indicators
    const bodyText = await page.locator('body').textContent();

    if (bodyText.includes('Extensions') || bodyText.includes('Wallet') || bodyText.includes('Add a new wallet')) {
      console.log('✅ Account creation successful - in wallet interface');

      // Try to access extensions
      console.log('🔌 Looking for Extensions menu...');

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
        await page.screenshot({ path: 'create-account-extensions.png', fullPage: true });
        console.log('📷 Extensions page: create-account-extensions.png');

        // Check if Allowance extension is visible
        const allowanceVisible = await page.locator('text=Allowance').isVisible();
        console.log('🔍 Allowance extension visible:', allowanceVisible);

        if (!allowanceVisible) {
          console.log('📝 Need to install Allowance extension...');
        }

      } else {
        console.log('❌ Could not find Extensions menu');
      }

    } else if (bodyText.includes('Invalid') || bodyText.includes('error')) {
      console.log('❌ Account creation failed');
      console.log('🔍 Error details:', bodyText.substring(0, 200));
    } else {
      console.log('❓ Unclear state after account creation');
      console.log('🔍 Body contains:', bodyText.substring(0, 200));
    }

  } catch (error) {
    console.error('❌ Error during account creation:', error.message);
    await page.screenshot({ path: 'create-account-error.png', fullPage: true });
    console.log('📷 Error screenshot: create-account-error.png');
  }

  await browser.close();
}

createAccount().catch(console.error);