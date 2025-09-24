const { chromium } = require('playwright');
const { getConfig, login } = require('./auth-helper');

(async () => {
  const config = getConfig();
  const browser = await chromium.launch({ headless: false });
  const page = await browser.newPage();

  try {
    await login(page);
    console.log('✅ Logged in');

    // Navigate to allowance extension
    await page.goto(`${config.baseUrl}/extensions`);
    await page.waitForTimeout(2000);
    const allowanceCard = page.locator('.q-card').filter({ hasText: 'allowance' }).first();
    await allowanceCard.click();
    await page.waitForTimeout(3000);

    // Find all buttons and print their text
    const buttons = await page.locator('button').all();
    console.log('📋 Found buttons:');
    for (const button of buttons) {
      const text = await button.textContent();
      if (text && text.trim()) {
        console.log(`  - "${text.trim()}"`);
      }
    }

    // Check for specific selectors
    console.log('\n🔍 Checking specific selectors:');
    console.log(`  button:has-text("New Allowance"): ${await page.locator('button:has-text("New Allowance")').count()}`);
    console.log(`  button:has-text("Create Allowance"): ${await page.locator('button:has-text("Create Allowance")').count()}`);
    console.log(`  button:has-text("Add"): ${await page.locator('button:has-text("Add")').count()}`);
    console.log(`  button:has-text("Create"): ${await page.locator('button:has-text("Create")').count()}`);

    await page.waitForTimeout(5000);

  } catch (error) {
    console.error('❌ Error:', error.message);
  } finally {
    await browser.close();
  }
})();
