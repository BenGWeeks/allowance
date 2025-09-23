const { chromium } = require('playwright');
const { login, getConfig } = require('./auth-helper');

async function diagnoseAuth() {
  const config = getConfig();

  console.log('🔍 Configuration loaded:');
  console.log('   URL:', config.baseUrl);
  console.log('   Username:', config.username);
  console.log('   Password length:', config.password?.length || 'undefined');

  const browser = await chromium.launch({ headless: false });
  const page = await browser.newPage();

  try {
    console.log('\n📝 Testing manual login steps...');

    // Go to the URL
    await page.goto(config.baseUrl);
    await page.waitForLoadState('networkidle');

    console.log('✅ Page loaded');
    console.log('   Current URL:', page.url());
    console.log('   Page title:', await page.title());

    // Take initial screenshot
    await page.screenshot({ path: 'diagnose-initial.png', fullPage: true });
    console.log('📷 Initial screenshot: diagnose-initial.png');

    // Check if we see "Create Account" - means we need to click Login
    const createAccountVisible = await page.locator('text=Create Account').first().isVisible();
    if (createAccountVisible) {
      console.log('📝 "Create Account" visible - clicking Login...');
      await page.click('text=Login');
      await page.waitForTimeout(2000);

      await page.screenshot({ path: 'diagnose-after-login-click.png', fullPage: true });
      console.log('📷 After Login click: diagnose-after-login-click.png');
    }

    // Check what login elements are visible
    const usernameField = await page.locator('input[type="text"], input[type="email"]').first();
    const passwordField = await page.locator('input[type="password"]').first();
    const loginButton = await page.locator('button:has-text("LOGIN")').first();

    console.log('🔍 Login form elements:');
    console.log('   Username field visible:', await usernameField.isVisible());
    console.log('   Password field visible:', await passwordField.isVisible());
    console.log('   Login button visible:', await loginButton.isVisible());

    // Fill in credentials step by step
    console.log('\n📝 Filling credentials...');
    await usernameField.fill(config.username);
    console.log('✅ Username filled');

    await passwordField.fill(config.password);
    console.log('✅ Password filled');

    await page.screenshot({ path: 'diagnose-credentials-filled.png', fullPage: true });
    console.log('📷 Credentials filled: diagnose-credentials-filled.png');

    // Click login and wait
    console.log('📝 Clicking LOGIN button...');
    await loginButton.click();
    await page.waitForTimeout(5000);

    await page.screenshot({ path: 'diagnose-after-login.png', fullPage: true });
    console.log('📷 After login: diagnose-after-login.png');

    // Check current state
    console.log('\n🔍 Post-login state:');
    console.log('   Current URL:', page.url());
    console.log('   Page title:', await page.title());

    // Check for success indicators
    const bodyText = await page.locator('body').textContent();

    if (bodyText.includes('Invalid credentials') || bodyText.includes('401 UNAUTHORIZED')) {
      console.log('❌ Authentication failed - invalid credentials detected');
    } else if (bodyText.includes('Add a new wallet') || bodyText.includes('Wallet') || bodyText.includes('Extensions')) {
      console.log('✅ Authentication appears successful');
    } else {
      console.log('❓ Unclear state - check screenshots');
      console.log('   Body contains (first 200 chars):', bodyText.substring(0, 200));
    }

  } catch (error) {
    console.error('❌ Error during diagnosis:', error.message);
    await page.screenshot({ path: 'diagnose-error.png', fullPage: true });
    console.log('📷 Error screenshot: diagnose-error.png');
  }

  await browser.close();
}

diagnoseAuth().catch(console.error);