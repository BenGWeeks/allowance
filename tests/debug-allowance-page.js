const { chromium } = require('playwright');

async function debugAllowancePage() {
  const browser = await chromium.launch({ headless: false });
  const context = await browser.newContext();
  const page = await context.newPage();

  try {
    console.log('🐛 Debugging allowance page load...');
    
    // Capture console errors
    page.on('console', msg => {
      if (msg.type() === 'error') {
        console.log('💥 Console error:', msg.text());
      }
    });

    page.on('pageerror', error => {
      console.log('💥 Page error:', error.message);
    });
    
    // Login
    await page.goto('http://localhost:5001/');
    await page.waitForLoadState('networkidle');
    
    const createAccountVisible = await page.locator('text=Create Account').first().isVisible();
    if (createAccountVisible) {
      console.log('🔄 Switching to login...');
      await page.click('text=Login');
      await page.waitForTimeout(2000);
    }
    
    console.log('🔑 Logging in...');
    await page.fill('input[type="text"], input[type="email"]', 'ben.weeks');
    await page.fill('input[type="password"]', 'zUYmy&05&uZ$3kmf*^T8');
    await page.click('button:has-text("LOGIN")');
    await page.waitForTimeout(3000);

    console.log('🎯 Navigating to allowance extension...');
    await page.goto('http://localhost:5001/allowance');
    
    // Wait longer and check what's on the page
    await page.waitForTimeout(5000);
    
    console.log('📍 Current URL:', page.url());
    
    // Check page content
    const pageContent = await page.textContent('body');
    console.log('📄 Page contains "Allowance":', pageContent.includes('Allowance'));
    console.log('📄 Page contains "New Allowance":', pageContent.includes('New Allowance'));
    console.log('📄 Page contains error keywords:', 
      pageContent.includes('Error') || 
      pageContent.includes('localStorage') || 
      pageContent.includes('undefined'));
    
    // Check for specific elements
    const newAllowanceButton = await page.locator('button:has-text("New Allowance")').count();
    const vueElement = await page.locator('#vue').count();
    const errorElements = await page.locator('[class*="error"]').count();
    
    console.log('🔍 Element counts:');
    console.log('  New Allowance button:', newAllowanceButton);
    console.log('  #vue element:', vueElement);
    console.log('  Error elements:', errorElements);
    
    // Take screenshot
    await page.screenshot({ path: 'tests/test-results/debug-allowance-page.png' });
    
    // Check Vue app state
    const vueState = await page.evaluate(() => {
      return {
        windowApp: typeof window.app !== 'undefined',
        vueExists: typeof Vue !== 'undefined',
        appMounted: !!(window.app && window.app.$el),
        errors: window.lastError || 'No errors stored'
      };
    });
    
    console.log('🔍 Vue state:', JSON.stringify(vueState, null, 2));
    
    // If there are no buttons, show what's actually in the body
    if (newAllowanceButton === 0) {
      const bodyText = await page.textContent('body');
      console.log('📄 First 500 chars of page content:');
      console.log(bodyText.substring(0, 500));
    }

  } catch (error) {
    console.error('❌ Debug failed:', error);
    await page.screenshot({ path: 'tests/test-results/debug-error.png' });
  } finally {
    // Don't close browser for manual inspection
    console.log('🔍 Browser left open for manual inspection...');
    // await browser.close();
  }
}

debugAllowancePage();