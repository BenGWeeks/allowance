const { chromium } = require('playwright');
const { login, getConfig } = require('./auth-helper');

async function testAllowanceAccess() {
  const config = getConfig();
  const browser = await chromium.launch({ headless: false });
  const page = await browser.newPage();

  try {
    console.log('🔍 Testing Allowance extension access...');

    // Login first
    await login(page);

    // Click on Allowance in the left navigation
    console.log('📝 Looking for Allowance in left navigation...');

    // Look for Allowance link in the sidebar
    const allowanceSelectors = [
      'text=Allowance',
      '.q-item:has-text("Allowance")',
      'a[href*="allowance"]',
      '.q-item__label:has-text("Allowance")'
    ];

    let found = false;
    for (const selector of allowanceSelectors) {
      try {
        if (await page.locator(selector).isVisible({ timeout: 2000 })) {
          console.log(`✅ Found Allowance using selector: ${selector}`);
          await page.locator(selector).click();
          await page.waitForTimeout(3000);
          found = true;
          break;
        }
      } catch (error) {
        // Continue to next selector
      }
    }

    if (!found) {
      console.log('❌ Could not find Allowance in navigation');
      await page.screenshot({ path: 'test-allowance-nav-missing.png', fullPage: true });
      console.log('📷 Navigation screenshot: test-allowance-nav-missing.png');
      return false;
    }

    console.log('✅ Successfully clicked on Allowance in navigation');

    const currentUrl = page.url();
    console.log('Current URL after navigation:', currentUrl);

    await page.screenshot({ path: 'test-allowance-access.png', fullPage: true });
    console.log('📷 Screenshot: test-allowance-access.png');

    // Check if we got redirected or if content loaded
    const pageContent = await page.content();
    if (pageContent.includes('404') || pageContent.includes('Not Found')) {
      console.log('❌ Extension not accessible - 404 error');
      return false;
    } else if (pageContent.includes('Allowance') || currentUrl.includes('/allowance')) {
      console.log('✅ Allowance extension accessible');
      console.log('Extension URL:', currentUrl);
      return true;
    } else {
      console.log('⚠️ Unexpected page content');
      console.log('Page title:', await page.title());
      return false;
    }

  } catch (error) {
    console.error('❌ Error testing allowance access:', error.message);
    await page.screenshot({ path: 'test-allowance-access-error.png', fullPage: true });
    console.log('📷 Error screenshot: test-allowance-access-error.png');
    return false;
  } finally {
    await browser.close();
  }
}

testAllowanceAccess()
  .then(success => {
    console.log('Test result:', success ? 'PASS' : 'FAIL');
    process.exit(success ? 0 : 1);
  })
  .catch(error => {
    console.error('Test failed:', error.message);
    process.exit(1);
  });