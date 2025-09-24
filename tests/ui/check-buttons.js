const { chromium } = require('playwright');
const { getConfig, login } = require('./auth-helper');

(async () => {
  const config = getConfig();
  const browser = await chromium.launch({ headless: true });
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
    const buttons = await page.$$eval('button', btns =>
      btns.map(b => b.textContent?.trim()).filter(t => t)
    );

    console.log('📋 Found buttons:');
    buttons.forEach(text => console.log(`  - "${text}"`));

    // Check if table exists
    const tableExists = await page.locator('table').count() > 0;
    console.log(`\n📊 Table exists: ${tableExists}`);

    // Check for plus/add icons
    const plusIcons = await page.locator('[class*="plus"], [class*="add"]').count();
    console.log(`➕ Plus/Add icons found: ${plusIcons}`);

  } catch (error) {
    console.error('❌ Error:', error.message);
  } finally {
    await browser.close();
  }
})();