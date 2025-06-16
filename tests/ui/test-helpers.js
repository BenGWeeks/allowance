/**
 * Test helper functions for UI tests
 */

/**
 * Get admin API key by extracting from the LNBits UI
 * @param {Page} page - Playwright page object
 * @returns {Promise<string|null>} - Admin API key or null if not found
 */
async function getAdminApiKey(page) {
  try {
    // Navigate to the main wallet page where API keys are displayed
    await page.goto('http://localhost:5001/');
    await page.waitForTimeout(2000);
    
    // Look for API key in the UI (it might be in a data attribute or text content)
    const apiKey = await page.evaluate(() => {
      // Try to find API key in various locations
      const keyElements = document.querySelectorAll('[data-cy="admin-key"], [data-cy="api-key"], .api-key');
      for (const el of keyElements) {
        const key = el.textContent || el.getAttribute('data-key') || el.value;
        if (key && key.length > 10) {
          return key.trim();
        }
      }
      
      // Try to find it in the page source
      const pageText = document.body.textContent;
      const keyMatch = pageText.match(/[a-f0-9]{32}/); // Look for 32-char hex string
      return keyMatch ? keyMatch[0] : null;
    });
    
    return apiKey;
  } catch (error) {
    console.log(`⚠️ Error getting API key: ${error.message}`);
    return null;
  }
}

/**
 * Get allowance count via API endpoint
 * @param {Page} page - Playwright page object
 * @returns {Promise<number>} - Number of allowances
 */
async function getAllowanceCount(page) {
  try {
    // For now, use the known development environment behavior
    // TODO: Get actual API key dynamically
    const response = await page.request.get('http://localhost:5001/allowance/api/v1/allowance', {
      headers: {
        'X-Api-Key': 'd16c6bf31be03c2cd0cfadc7d90a2d69' // Development key
      }
    });
    
    if (response.ok()) {
      const data = await response.json();
      return Array.isArray(data) ? data.length : 0;
    } else {
      console.log(`⚠️ API request failed: ${response.status()}`);
      return 0;
    }
  } catch (error) {
    console.log(`⚠️ Error getting allowance count: ${error.message}`);
    return 0;
  }
}

/**
 * Get allowances data via API endpoint
 * @param {Page} page - Playwright page object
 * @returns {Promise<Array>} - Array of allowances
 */
async function getAllowances(page) {
  try {
    const response = await page.request.get('http://localhost:5001/allowance/api/v1/allowance', {
      headers: {
        'X-Api-Key': 'd16c6bf31be03c2cd0cfadc7d90a2d69' // Development key
      }
    });
    
    if (response.ok()) {
      const data = await response.json();
      return Array.isArray(data) ? data : [];
    } else {
      console.log(`⚠️ API request failed: ${response.status()}`);
      return [];
    }
  } catch (error) {
    console.log(`⚠️ Error getting allowances: ${error.message}`);
    return [];
  }
}

/**
 * Find an allowance by name
 * @param {Page} page - Playwright page object
 * @param {string} name - Name to search for
 * @returns {Promise<Object|null>} - Allowance object or null if not found
 */
async function findAllowanceByName(page, name) {
  const allowances = await getAllowances(page);
  return allowances.find(allowance => allowance.name === name) || null;
}

/**
 * Get an allowance by ID
 * @param {Page} page - Playwright page object
 * @param {string} id - Allowance ID
 * @returns {Promise<Object|null>} - Allowance object or null if not found
 */
async function getAllowanceById(page, id) {
  const allowances = await getAllowances(page);
  return allowances.find(allowance => allowance.id === id) || null;
}

/**
 * Login helper function
 * @param {Page} page - Playwright page object
 * @param {string} username - Username (default: ben.weeks)
 * @param {string} password - Password (default: zUYmy&05&uZ$3kmf*^T8)
 */
async function loginAsAdmin(page, username = 'ben.weeks', password = 'zUYmy&05&uZ$3kmf*^T8') {
  console.log('📝 Logging in as admin...');
  
  await page.goto('http://localhost:5001/');
  await page.waitForLoadState('networkidle');
  
  // Check if we need to switch to login screen
  const createAccountVisible = await page.locator('text=Create Account').first().isVisible();
  if (createAccountVisible) {
    await page.click('text=Login');
    await page.waitForTimeout(2000);
  }
  
  // Fill login credentials
  await page.fill('input[type="text"], input[type="email"]', username);
  await page.fill('input[type="password"]', password);
  await page.click('button:has-text("LOGIN")');
  await page.waitForTimeout(3000);
  
  // Verify login success
  const isLoggedIn = await page.locator('text=Add a new wallet').isVisible();
  if (!isLoggedIn) {
    throw new Error('Login failed - could not find "Add a new wallet" text');
  }
  
  console.log('✅ Successfully logged in');
}

/**
 * Navigate to allowance extension
 * @param {Page} page - Playwright page object
 */
async function navigateToAllowance(page) {
  console.log('📝 Navigating to allowance extension...');
  
  await page.goto('http://localhost:5001/allowance/');
  await page.waitForTimeout(3000);
  
  // Verify we're on the allowance page by looking for the heading
  const isOnAllowancePage = await page.locator('h5:has-text("Allowances")').isVisible();
  if (!isOnAllowancePage) {
    throw new Error('Failed to navigate to allowance page');
  }
  
  console.log('✅ Successfully navigated to allowance page');
}

/**
 * Wait for API response and verify count change
 * @param {Page} page - Playwright page object
 * @param {number} expectedChange - Expected change in count (+1 for create, -1 for delete, 0 for edit)
 * @param {number} initialCount - Initial count before operation
 * @param {number} maxWaitMs - Maximum wait time in milliseconds (default: 10000)
 */
async function waitForCountChange(page, expectedChange, initialCount, maxWaitMs = 10000) {
  const startTime = Date.now();
  
  while (Date.now() - startTime < maxWaitMs) {
    const currentCount = await getAllowanceCount(page);
    const actualChange = currentCount - initialCount;
    
    if (actualChange === expectedChange) {
      console.log(`✅ Count changed as expected: ${initialCount} -> ${currentCount} (${actualChange >= 0 ? '+' : ''}${actualChange})`);
      return true;
    }
    
    await page.waitForTimeout(500);
  }
  
  const finalCount = await getAllowanceCount(page);
  const actualChange = finalCount - initialCount;
  console.log(`❌ Count change timeout: expected ${expectedChange}, got ${actualChange} (${initialCount} -> ${finalCount})`);
  return false;
}

module.exports = {
  getAdminApiKey,
  getAllowanceCount,
  getAllowances,
  findAllowanceByName,
  getAllowanceById,
  loginAsAdmin,
  navigateToAllowance,
  waitForCountChange
};