/**
 * Helper to get API key from LNBits using username/password authentication.
 * This avoids hardcoding API keys in tests.
 */

const USERNAME = 'ben.weeks';
const PASSWORD = 'zUYmy&05&uZ$3kmf*^T8';
const LNBITS_URL = 'http://localhost:5001';

/**
 * Get the admin API key using username/password authentication
 * @param {Page} page - Playwright page object (optional, for context)
 * @returns {Promise<string|null>} - Admin API key or null if failed
 */
async function getAdminApiKey(page = null) {
  try {
    // Use page.request directly if page is provided, otherwise create new context
    let apiContext;
    if (page) {
      apiContext = page.request;
    } else {
      const { request } = require('playwright');
      apiContext = await request.newContext();
    }
    
    // Step 1: Login to get access token
    const loginResponse = await apiContext.post(`${LNBITS_URL}/api/v1/auth`, {
      data: {
        username: USERNAME,
        password: PASSWORD
      }
    });
    
    if (!loginResponse.ok()) {
      console.log(`❌ Login failed: ${loginResponse.status()}`);
      return null;
    }
    
    const authData = await loginResponse.json();
    const accessToken = authData.access_token;
    
    if (!accessToken) {
      console.log('❌ No access token received');
      return null;
    }
    
    // Step 2: Get wallets using the access token
    const walletsResponse = await apiContext.get(`${LNBITS_URL}/api/v1/wallets`, {
      headers: {
        'Authorization': `Bearer ${accessToken}`
      }
    });
    
    if (!walletsResponse.ok()) {
      console.log(`❌ Failed to get wallets: ${walletsResponse.status()}`);
      return null;
    }
    
    const wallets = await walletsResponse.json();
    
    if (!wallets || wallets.length === 0) {
      console.log('❌ No wallets found');
      return null;
    }
    
    // Return the admin key from the first wallet
    const adminWallet = wallets[0];
    const adminKey = adminWallet.adminkey;
    const walletId = adminWallet.id;
    
    console.log(`✅ Found admin wallet: ${walletId}`);
    console.log(`✅ Admin API key: ${adminKey}`);
    
    // Only dispose if we created our own context
    if (!page && apiContext.dispose) {
      await apiContext.dispose();
    }
    return adminKey;
    
  } catch (error) {
    console.log(`❌ Error getting API key: ${error.message}`);
    return null;
  }
}

module.exports = {
  getAdminApiKey
};