const { chromium } = require('playwright');

async function testUIRenders() {
  const browser = await chromium.launch({ headless: false });
  const context = await browser.newContext();
  const page = await context.newPage();

  try {
    console.log('🧪 Testing if UI renders properly after windowMixin fix...');
    
    // Capture console errors
    const errors = [];
    page.on('console', msg => {
      if (msg.type() === 'error') {
        errors.push(msg.text());
        console.log('💥 Error:', msg.text());
      }
    });

    page.on('pageerror', error => {
      errors.push(error.message);
      console.log('💥 Page error:', error.message);
    });
    
    // Login
    await page.goto('http://localhost:5001/');
    await page.waitForLoadState('networkidle');
    
    const createAccountVisible = await page.locator('text=Create Account').first().isVisible();
    if (createAccountVisible) {
      await page.click('text=Login');
      await page.waitForTimeout(2000);
    }
    
    await page.fill('input[type="text"], input[type="email"]', 'ben.weeks');
    await page.fill('input[type="password"]', 'zUYmy&05&uZ$3kmf*^T8');
    await page.click('button:has-text("LOGIN")');
    await page.waitForTimeout(3000);

    // Navigate to allowance
    console.log('🎯 Navigating to allowance extension...');
    await page.goto('http://localhost:5001/allowance');
    await page.waitForTimeout(5000);
    
    // Check what's actually rendered
    const pageContent = await page.textContent('body');
    const hasAllowanceContent = pageContent.includes('Allowance');
    const hasNewAllowanceButton = pageContent.includes('New Allowance');
    const hasErrorContent = pageContent.includes('Error') || pageContent.includes('404');
    
    console.log('📄 Page analysis:');
    console.log('  Contains "Allowance":', hasAllowanceContent);
    console.log('  Contains "New Allowance":', hasNewAllowanceButton);
    console.log('  Contains error content:', hasErrorContent);
    console.log('  Page length:', pageContent.length);
    
    // Check specific UI elements
    const newAllowanceBtn = await page.locator('button:has-text("New Allowance")').count();
    const allowanceTable = await page.locator('.q-table').count();
    const vueElement = await page.locator('#vue').count();
    
    console.log('🔍 UI Elements:');
    console.log('  New Allowance button:', newAllowanceBtn);
    console.log('  Allowance table:', allowanceTable);
    console.log('  #vue element:', vueElement);
    
    // Check Vue app state
    const vueState = await page.evaluate(() => {
      return {
        appExists: typeof window.app !== 'undefined',
        saveAllowanceExists: window.app && typeof window.app.saveAllowance === 'function',
        gExists: window.app && window.app.g,
        walletsCount: window.app && window.app.g && window.app.g.user ? window.app.g.user.wallets.length : 0
      };
    });
    
    console.log('🔍 Vue app state:', JSON.stringify(vueState, null, 2));
    
    // Take screenshot
    await page.screenshot({ path: 'tests/test-results/ui-render-test.png' });
    
    console.log(`💥 Total errors captured: ${errors.length}`);
    if (errors.length > 0) {
      console.log('❌ Errors found:');
      errors.forEach((error, i) => {
        console.log(`  ${i + 1}. ${error}`);
      });
    }
    
    // Summary
    if (newAllowanceBtn > 0 && errors.length === 0) {
      console.log('✅ SUCCESS: UI renders properly with no errors!');
    } else if (newAllowanceBtn > 0 && errors.length > 0) {
      console.log('⚠️ PARTIAL: UI renders but has errors');
    } else {
      console.log('❌ FAILED: UI not rendering properly');
      
      // Show first 200 chars of actual content
      console.log('📄 Actual page content:');
      console.log(pageContent.substring(0, 500));
    }

  } catch (error) {
    console.error('❌ UI render test failed:', error);
    await page.screenshot({ path: 'tests/test-results/ui-render-error.png' });
  } finally {
    console.log('🔍 Leaving browser open for inspection...');
    // await browser.close();
  }
}

testUIRenders();