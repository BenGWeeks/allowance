#!/usr/bin/env node

const { chromium } = require('playwright');
const { getConfig } = require('./auth-helper');

async function testWithAuth() {
  const browser = await chromium.launch({
    headless: false,
    slowMo: 100
  });
  const context = await browser.newContext();
  const page = await context.newPage();
  const config = getConfig();

  try {
    console.log('Testing authentication flow...');
    console.log('URL:', config.baseUrl);
    console.log('Username:', config.username);
    console.log('Password:', config.password);

    // Navigate to base URL
    await page.goto(config.baseUrl);
    await page.waitForLoadState('networkidle');

    // Screenshot initial page
    await page.screenshot({ path: 'test-auth-1-initial.png', fullPage: true });
    console.log('Initial URL:', page.url());
    console.log('Screenshot saved: test-auth-1-initial.png');

    // Check if we see the create account page
    if (await page.locator('text="Create account"').isVisible()) {
      console.log('On create account page, clicking Login link...');

      // Click on the Login link
      const loginLink = page.locator('a:has-text("Login"), text="Login"').last();
      if (await loginLink.isVisible()) {
        await loginLink.click();
        await page.waitForLoadState('networkidle');

        // Screenshot after clicking login
        await page.screenshot({ path: 'test-auth-2-login-page.png', fullPage: true });
        console.log('Screenshot saved: test-auth-2-login-page.png');
      }
    }

    // Now try to find login form
    const usernameInput = await page.locator('input[type="text"], input[name="username"], input[id="username"]').first();
    const passwordInput = await page.locator('input[type="password"], input[name="password"], input[id="password"]').first();

    if (await usernameInput.isVisible() && await passwordInput.isVisible()) {
      console.log('Found login form, filling credentials...');

      await usernameInput.fill(config.username);
      await passwordInput.fill(config.password);

      // Screenshot after filling
      await page.screenshot({ path: 'test-auth-3-filled.png', fullPage: true });
      console.log('Screenshot saved: test-auth-3-filled.png');

      // Find and click login button - wait for it to be enabled
      const loginButton = await page.locator('button:has-text("Login"), button:has-text("Sign in"), button[type="submit"]').first();

      // Wait for button to be enabled
      await page.waitForFunction(
        (selector) => {
          const btn = document.querySelector(selector);
          return btn && !btn.disabled;
        },
        'button:has-text("Login"), button[type="submit"]',
        { timeout: 5000 }
      ).catch(() => {
        console.log('Button did not become enabled, trying anyway...');
      });

      if (await loginButton.isVisible()) {
        await loginButton.click();
        console.log('Clicked login button');

        // Wait for navigation
        await page.waitForLoadState('networkidle', { timeout: 10000 });

        // Screenshot after login
        await page.screenshot({ path: 'test-auth-4-after-login.png', fullPage: true });
        const afterLoginUrl = page.url();
        console.log('After login URL:', afterLoginUrl);
        console.log('Screenshot saved: test-auth-4-after-login.png');

        if (afterLoginUrl.includes('/wallet') || afterLoginUrl.includes('/admin')) {
          console.log('✅ Login successful!');
          await page.screenshot({ path: 'test-auth-5-success.png', fullPage: true });
        } else {
          console.log('❌ Login may have failed');

          // Check for errors
          const errors = await page.locator('.q-notification__message, .error, [role="alert"]').allTextContents();
          if (errors.length > 0) {
            console.log('Error messages:', errors);
          }
        }
      }
    } else {
      console.log('No login form found');
    }

    // Complete notification
    console.log('Sending completion notification...');
    await browser.close();
    return 0;

  } catch (error) {
    console.error('❌ Error:', error.message);
    await page.screenshot({ path: 'test-auth-error.png', fullPage: true });
    await browser.close();
    return 1;
  }
}

// Run the test
testWithAuth().then(exitCode => {
  if (exitCode === 0) {
    // Success - notify user with sound
    require('child_process').exec('canberra-gtk-play -i complete', (err) => {
      if (err) console.log('Could not play notification sound');
    });
  }
  process.exit(exitCode);
});