const { chromium } = require('playwright');

async function quickVueCheck() {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext();
  const page = await context.newPage();

  try {
    console.log('🔍 Quick Vue state check...');
    
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

    await page.goto('http://localhost:5001/allowance');
    await page.waitForTimeout(3000);
    
    // Quick Vue state check
    const vueState = await page.evaluate(() => {
      return {
        windowApp: typeof window.app !== 'undefined',
        vueInstance: !!(window.app && window.app._instance),
        saveAllowance: window.app && typeof window.app.saveAllowance === 'function',
        openCreateDialog: window.app && typeof window.app.openCreateDialog === 'function',
        gExists: !!(window.app && window.app.g),
        walletsCount: window.app && window.app.g && window.app.g.user ? window.app.g.user.wallets.length : 0
      };
    });
    
    console.log('🔍 Vue state:', JSON.stringify(vueState, null, 2));
    
    // Try to manually call a method
    const manualCall = await page.evaluate(() => {
      try {
        if (window.app && window.app.openCreateDialog) {
          window.app.openCreateDialog();
          return 'Method called successfully';
        } else {
          return 'Method not found';
        }
      } catch (error) {
        return `Error: ${error.message}`;
      }
    });
    
    console.log('🧪 Manual method call result:', manualCall);
    
    await page.waitForTimeout(2000);
    
    // Check if dialog opened
    const dialogVisible = await page.locator('.q-dialog').isVisible();
    console.log('📋 Dialog opened after manual call:', dialogVisible);

  } catch (error) {
    console.error('❌ Quick check failed:', error);
  } finally {
    await browser.close();
  }
}

quickVueCheck();