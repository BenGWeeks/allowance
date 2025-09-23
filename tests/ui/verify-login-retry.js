const { chromium } = require('playwright');
const { getConfig } = require('./auth-helper');

async function carefulLogin() {
  const config = getConfig();
  const browser = await chromium.launch({ headless: false, slowMo: 500 });
  const page = await browser.newPage();

  try {
    console.log('🔌 Careful login attempt...');
    console.log('   Username:', config.username);
    console.log('   Password:', '*'.repeat(config.password.length));

    await page.goto(config.baseUrl);
    await page.waitForLoadState('networkidle');

    // Click Login link
    await page.click('text=Login');
    await page.waitForTimeout(3000);

    console.log('📝 Very careful form filling...');

    // Clear and fill username with extra care
    const usernameField = page.locator('input[type="text"], input[type="email"]').first();
    await usernameField.click();
    await usernameField.fill('');
    await page.waitForTimeout(500);
    await usernameField.type(config.username, { delay: 100 });
    await page.waitForTimeout(1000);

    // Clear and fill password with extra care
    const passwordField = page.locator('input[type="password"]').first();
    await passwordField.click();
    await passwordField.fill('');
    await page.waitForTimeout(500);
    await passwordField.type(config.password, { delay: 100 });
    await page.waitForTimeout(1000);

    await page.screenshot({ path: 'careful-login-filled.png', fullPage: true });
    console.log('📷 Careful form filled: careful-login-filled.png');

    // Click login button
    console.log('📝 Clicking LOGIN...');
    await page.click('button:has-text("LOGIN")');

    // Wait longer and watch for changes
    console.log('⏰ Waiting for response...');
    await page.waitForTimeout(8000);

    await page.screenshot({ path: 'careful-login-result.png', fullPage: true });
    console.log('📷 Login result: careful-login-result.png');

    // Check current state very carefully
    const url = page.url();
    const title = await page.title();
    const bodyText = await page.locator('body').textContent();

    console.log('🔍 Final state:');
    console.log('   URL:', url);
    console.log('   Title:', title);

    // Look for specific success/failure indicators
    if (bodyText.includes('Invalid credentials') || bodyText.includes('401')) {
      console.log('❌ Login failed - invalid credentials');
    } else if (bodyText.includes('Extensions') || bodyText.includes('ben.weeks')) {
      console.log('✅ Login appears successful');
    } else {
      console.log('❓ Unclear result');
      console.log('   Content sample:', bodyText.substring(0, 300));
    }

  } catch (error) {
    console.error('❌ Error:', error.message);
    await page.screenshot({ path: 'careful-login-error.png', fullPage: true });
  }

  await browser.close();
}

carefulLogin().catch(console.error);