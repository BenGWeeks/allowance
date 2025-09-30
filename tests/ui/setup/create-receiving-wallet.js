const { chromium } = require('playwright');
const { login, getConfig } = require('../auth-helper');

async function createReceivingWallet() {
  const config = getConfig();
  const browser = await chromium.launch({ headless: false });
  const page = await browser.newPage();
  const walletName = process.env.RECEIVING_WALLET_NAME || 'Receiving';

  try {
    console.log('🔍 Creating receiving wallet...');

    // Login first
    await login(page);

    // Close the "Important!" dialog if present
    try {
      const understandButton = page.locator('button:has-text("I UNDERSTAND")');
      if (await understandButton.isVisible({ timeout: 2000 })) {
        await understandButton.click();
        console.log('✅ Closed Important dialog');
        await page.waitForTimeout(1000);
      }
    } catch (e) {
      // Dialog not present, continue
    }

    // Check if the wallet creation form is already open
    const walletNameInput = page.locator('input[aria-label*="Name wallet"]');
    if (await walletNameInput.isVisible({ timeout: 2000 })) {
      console.log('📝 Wallet creation form already open');
      await walletNameInput.fill(walletName);
      console.log(`📝 Set wallet name: ${walletName}`);
      await walletNameInput.press('Enter');
      await page.waitForTimeout(3000);

      // Verify wallet was created
      const newWallet = page.locator(`text="${walletName}"`).first();
      if (await newWallet.isVisible({ timeout: 5000 })) {
        console.log(`✅ ${walletName} wallet created successfully`);
        await browser.close();
        return true;
      }
    }

    // Check if we already have a wallet called "Receiving"
    console.log(`📝 Checking for existing ${walletName} wallet...`);
    await page.waitForTimeout(2000);
    
    const existingWallet = page.locator(`text="${walletName}"`).first();
    if (await existingWallet.isVisible({ timeout: 3000 }).catch(() => false)) {
      console.log(`✅ ${walletName} wallet already exists`);
      await browser.close();
      return true;
    }

    // Click on "Add a new wallet" in the left navigation
    console.log('📝 Creating new wallet...');
    const addWalletButton = page.locator('text="Add a new wallet"').first();

    if (await addWalletButton.isVisible()) {
      await addWalletButton.click();
      await page.waitForTimeout(2000);

      // Fill in wallet name
      const walletNameInput = page.locator('input').first();
      await walletNameInput.fill(walletName);
      console.log(`📝 Set wallet name: ${walletName}`);

      // Submit form - just press Enter
      await walletNameInput.press('Enter');
      await page.waitForTimeout(3000);

      // Verify wallet was created
      const newWallet = page.locator(`text="${walletName}"`).first();
      if (await newWallet.isVisible({ timeout: 5000 })) {
        console.log(`✅ ${walletName} wallet created successfully`);
        return true;
      } else {
        console.log('❌ Failed to create receiving wallet');
        return false;
      }
    } else {
      console.log('❌ Add wallet button not found');
      await page.screenshot({ path: 'test-add-wallet-not-found.png', fullPage: true });
      return false;
    }

  } catch (error) {
    console.error('❌ Error creating receiving wallet:', error.message);
    await page.screenshot({ path: 'test-receiving-wallet-error.png', fullPage: true });
    return false;
  } finally {
    await browser.close();
  }
}

createReceivingWallet()
  .then(success => {
    console.log('Result:', success ? 'PASS' : 'FAIL');
    process.exit(success ? 0 : 1);
  })
  .catch(error => {
    console.error('Test failed:', error.message);
    process.exit(1);
  });
