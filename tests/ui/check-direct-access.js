const { chromium } = require('playwright');
const { getConfig } = require('./auth-helper');

async function checkDirectAccess() {
  const config = getConfig();
  const browser = await chromium.launch({ headless: false });
  const page = await browser.newPage();

  try {
    console.log('🔌 Testing direct access to LNBits endpoints...');

    // Try different URLs to see what's accessible
    const urlsToTry = [
      config.baseUrl,
      config.baseUrl + '/wallet',
      config.baseUrl + '/extensions',
      config.baseUrl + '/extensions/allowance'
    ];

    for (const url of urlsToTry) {
      console.log(`\n📝 Trying: ${url}`);

      try {
        await page.goto(url);
        await page.waitForLoadState('networkidle');

        const title = await page.title();
        const currentUrl = page.url();

        console.log(`   Title: ${title}`);
        console.log(`   Final URL: ${currentUrl}`);

        const bodyText = await page.locator('body').textContent();

        if (bodyText.includes('Login') || bodyText.includes('Create account')) {
          console.log('   Status: Redirected to login page');
        } else if (bodyText.includes('Extensions') || bodyText.includes('Wallet')) {
          console.log('   Status: ✅ Accessible - in wallet interface');

          await page.screenshot({ path: `direct-access-${url.split('/').pop() || 'root'}.png`, fullPage: true });
          console.log(`   📷 Screenshot saved`);

          // If we're on extensions page, check for Allowance
          if (bodyText.includes('Allowance')) {
            console.log('   🎯 Allowance extension found!');
          } else {
            console.log('   ❌ Allowance extension not visible');
          }

        } else if (bodyText.includes('404') || bodyText.includes('Not Found')) {
          console.log('   Status: ❌ 404 - Page not found');
        } else {
          console.log('   Status: ❓ Unknown page');
          console.log(`   Content sample: ${bodyText.substring(0, 100)}...`);
        }

      } catch (error) {
        console.log(`   Status: ❌ Error - ${error.message}`);
      }
    }

    // Also try to check if there are any existing sessions/cookies
    console.log('\n🍪 Checking cookies:');
    const cookies = await page.context().cookies();
    console.log(`   Found ${cookies.length} cookies`);

    for (const cookie of cookies) {
      console.log(`   - ${cookie.name}: ${cookie.value.substring(0, 20)}...`);
    }

  } catch (error) {
    console.error('❌ Error during direct access check:', error.message);
  }

  await browser.close();
}

checkDirectAccess().catch(console.error);