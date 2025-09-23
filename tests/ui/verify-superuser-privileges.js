const { chromium } = require('playwright');
const { login, getConfig } = require('./auth-helper');

async function testSuperuserPrivileges() {
  const config = getConfig();
  const browser = await chromium.launch({ headless: false });
  const page = await browser.newPage();

  try {
    console.log('🔍 Testing superuser privileges...');

    // Login first
    await login(page);

    // Log out to refresh session
    console.log('📝 Logging out to refresh session...');
    const logoutSelectors = [
      'button:has-text("Logout")',
      '.q-btn:has-text("Logout")',
      'text=Logout',
      '[data-cy="logout"]'
    ];

    let loggedOut = false;
    for (const selector of logoutSelectors) {
      try {
        if (await page.locator(selector).isVisible({ timeout: 2000 })) {
          console.log(`✅ Found logout using selector: ${selector}`);
          await page.locator(selector).click();
          await page.waitForTimeout(2000);
          loggedOut = true;
          break;
        }
      } catch (error) {
        // Continue to next selector
      }
    }

    if (!loggedOut) {
      console.log('⚠️ Could not find logout button, trying profile menu...');
      // Try clicking on profile menu first
      const profileSelectors = [
        '.q-btn:has(.q-avatar)',
        'button:has(.q-avatar)',
        '.q-avatar',
        '[data-cy="profile-menu"]'
      ];

      for (const selector of profileSelectors) {
        try {
          if (await page.locator(selector).isVisible({ timeout: 2000 })) {
            console.log(`📝 Clicking profile menu: ${selector}`);
            await page.locator(selector).click();
            await page.waitForTimeout(1000);

            // Now try logout again
            for (const logoutSelector of logoutSelectors) {
              try {
                if (await page.locator(logoutSelector).isVisible({ timeout: 2000 })) {
                  console.log(`✅ Found logout in menu: ${logoutSelector}`);
                  await page.locator(logoutSelector).click();
                  await page.waitForTimeout(2000);
                  loggedOut = true;
                  break;
                }
              } catch (error) {
                // Continue
              }
            }
            break;
          }
        } catch (error) {
          // Continue to next selector
        }
      }
    }

    if (loggedOut) {
      console.log('✅ Successfully logged out');
    } else {
      console.log('⚠️ Could not logout, proceeding anyway');
    }

    // Log back in
    console.log('📝 Logging back in...');
    await page.goto(config.baseUrl);
    await login(page);

    // Check for superuser indicators
    console.log('📝 Checking for superuser privileges...');

    // Look for admin-only features
    const adminIndicators = [
      'text=Extensions',  // Extensions menu should be visible for superusers
      'text=Users',       // User management
      'text=Admin',       // Admin panel
      'text=Server',      // Server settings
      '.q-item:has-text("Extensions")',
      '.q-item:has-text("Users")'
    ];

    let hasAdminFeatures = false;
    const foundFeatures = [];

    for (const indicator of adminIndicators) {
      try {
        if (await page.locator(indicator).isVisible({ timeout: 2000 })) {
          foundFeatures.push(indicator);
          hasAdminFeatures = true;
        }
      } catch (error) {
        // Continue checking
      }
    }

    await page.screenshot({ path: 'test-superuser-privileges.png', fullPage: true });
    console.log('📷 Screenshot: test-superuser-privileges.png');

    if (hasAdminFeatures) {
      console.log('✅ Superuser privileges confirmed');
      console.log('Found admin features:', foundFeatures);
      return true;
    } else {
      console.log('❌ No superuser privileges detected');
      console.log('Expected to find admin features like Extensions, Users, etc.');
      return false;
    }

  } catch (error) {
    console.error('❌ Error testing superuser privileges:', error.message);
    await page.screenshot({ path: 'test-superuser-error.png', fullPage: true });
    console.log('📷 Error screenshot: test-superuser-error.png');
    return false;
  } finally {
    await browser.close();
  }
}

testSuperuserPrivileges()
  .then(success => {
    console.log('Test result:', success ? 'PASS' : 'FAIL');
    process.exit(success ? 0 : 1);
  })
  .catch(error => {
    console.error('Test failed:', error.message);
    process.exit(1);
  });