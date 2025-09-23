/**
 * Authentication helper for UI tests
 * Centralizes configuration and login functionality
 */

const fs = require('fs');
const path = require('path');

/**
 * Load environment variables from .env.local
 */
function loadEnv() {
  const envPath = path.join(__dirname, '../../.env.local');
  const config = {};

  if (fs.existsSync(envPath)) {
    const content = fs.readFileSync(envPath, 'utf-8');
    const lines = content.split('\n');

    for (const line of lines) {
      if (line && !line.startsWith('#')) {
        const [key, value] = line.split('=');
        if (key && value) {
          config[key.trim()] = value.trim();
        }
      }
    }
  }

  return config;
}

/**
 * Get configuration for tests
 * @returns {Object} Configuration object with baseUrl, username, password
 */
function getConfig() {
  const config = loadEnv();

  // Use environment variables, no fallbacks to hardcoded values
  return {
    baseUrl: config.TEST_LNBITS_URL || process.env.TEST_LNBITS_URL,
    username: config.LNBITS_ADMIN_USERNAME || process.env.LNBITS_ADMIN_USERNAME,
    password: config.LNBITS_ADMIN_PASSWORD || process.env.LNBITS_ADMIN_PASSWORD,
    walletName: config.RECEIVING_WALLET_NAME || process.env.RECEIVING_WALLET_NAME || 'Receiving',
    payLinkEmail: config.PAYLINK_EMAIL || process.env.PAYLINK_EMAIL || `receiving@${(config.TEST_LNBITS_URL || process.env.TEST_LNBITS_URL || '').replace(/https?:\/\//, '')}`
  };
}

/**
 * Login to LNBits as admin user
 * @param {Page} page - Playwright page object
 */
async function login(page) {
  const config = getConfig();

  console.log('📝 Logging in as admin...');

  await page.goto(config.baseUrl);
  await page.waitForLoadState('networkidle');

  // Check if we need to switch to login screen
  const createAccountVisible = await page.locator('text=Create Account').first().isVisible();
  if (createAccountVisible) {
    await page.click('text=Login');
    await page.waitForTimeout(2000);
  }

  // Fill login credentials
  await page.fill('input[type="text"], input[type="email"]', config.username);
  await page.fill('input[type="password"]', config.password);
  await page.click('button:has-text("LOGIN")');
  await page.waitForTimeout(3000);

  // Verify login success - look for specific wallet interface indicators
  // Wait a bit longer for the page to fully load
  await page.waitForTimeout(2000);

  const indicators = [
    'text=Extensions',
    'text=Add a new wallet',
    'text=ben.weeks',  // User profile name
    '.q-btn:has-text("Add a new wallet")',
    '[data-cy="wallet-balance"]',
    'text=sats'  // Balance indicator
  ];

  let isLoggedIn = false;
  for (const indicator of indicators) {
    try {
      if (await page.locator(indicator).isVisible({ timeout: 5000 })) {
        isLoggedIn = true;
        console.log(`✅ Login verified using indicator: ${indicator}`);
        break;
      }
    } catch (error) {
      // Continue to next indicator
    }
  }

  if (!isLoggedIn) {
    // Take a screenshot for debugging
    await page.screenshot({ path: 'login-verification-failed.png', fullPage: true });
    console.log('📷 Screenshot saved: login-verification-failed.png');
    console.log('🔍 Current URL:', page.url());
    console.log('🔍 Page title:', await page.title());

    // Get some page content for debugging
    const bodyText = await page.locator('body').textContent();
    console.log('🔍 Page contains:', bodyText.substring(0, 500));

    throw new Error('Login failed - could not verify successful login');
  }

  console.log('✅ Successfully logged in');
}

module.exports = {
  login,
  getConfig
};