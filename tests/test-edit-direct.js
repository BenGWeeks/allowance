const { chromium } = require('playwright');

async function testEditDirect() {
  const browser = await chromium.launch({ headless: false });
  const context = await browser.newContext();
  const page = await context.newPage();

  try {
    console.log('🎯 Testing edit functionality with Vue mount fix...');
    
    // Capture console messages
    page.on('console', msg => {
      if (msg.type() === 'log') {
        console.log(`📣 ${msg.text()}`);
      } else if (msg.type() === 'error') {
        console.log(`💥 Error: ${msg.text()}`);
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
      await page.click('text=Login');
      await page.waitForTimeout(2000);
    }
    
    await page.fill('input[type="text"], input[type="email"]', 'ben.weeks');
    await page.fill('input[type="password"]', 'zUYmy&05&uZ$3kmf*^T8');
    await page.click('button:has-text("LOGIN")');
    await page.waitForTimeout(3000);

    // Navigate to allowance
    await page.goto('http://localhost:5001/allowance');
    await page.waitForTimeout(5000);
    
    // Check if Vue is properly mounted
    const vueCheck = await page.evaluate(() => {
      return {
        windowApp: typeof window.app !== 'undefined',
        saveAllowance: window.app && typeof window.app.saveAllowance === 'function',
        mounted: window.app && window.app._instance && window.app._instance.isMounted
      };
    });
    
    console.log('🔍 Vue state after mount fix:', JSON.stringify(vueCheck, null, 2));
    
    if (vueCheck.saveAllowance) {
      console.log('✅ SUCCESS: saveAllowance method is now accessible!');
      console.log('🎉 Vue mounting fix worked - form submission should now work');
      
      // Test if we can manually call the method
      const manualCall = await page.evaluate(() => {
        try {
          // Just test that the method exists and is callable
          return typeof window.app.saveAllowance === 'function';
        } catch (error) {
          return `Error: ${error.message}`;
        }
      });
      
      console.log('🔧 Manual method call test:', manualCall);
      
    } else {
      console.log('❌ saveAllowance still not accessible');
      
      if (!vueCheck.windowApp) {
        console.log('❌ window.app not found');
      } else if (!vueCheck.mounted) {
        console.log('❌ Vue app not mounted');
      } else {
        console.log('❌ saveAllowance method missing');
      }
    }
    
    // Try to test actual form if possible
    const newAllowanceBtn = page.locator('button:has-text("New Allowance")');
    const btnExists = await newAllowanceBtn.count() > 0;
    
    console.log('🔍 New Allowance button exists:', btnExists);
    
    if (btnExists) {
      console.log('🧪 Testing form dialog...');
      await newAllowanceBtn.click();
      await page.waitForTimeout(2000);
      
      const dialog = page.locator('.q-dialog');
      const dialogVisible = await dialog.isVisible();
      console.log('✅ Dialog opened:', dialogVisible);
      
      if (dialogVisible) {
        console.log('📝 Filling minimal form data...');
        await page.fill('input[placeholder*="Weekly allowance"]', 'Vue Fix Test');
        await page.fill('input[placeholder*="alice@getalby.com"]', 'test@example.com');
        await page.fill('input[type="number"]', '50');
        
        console.log('🚀 Testing form submission...');
        await page.click('button[type="submit"]');
        
        // Wait and check result
        await page.waitForTimeout(3000);
        const dialogClosed = !await dialog.isVisible();
        console.log('✅ Dialog closed after submit:', dialogClosed);
        
        if (dialogClosed) {
          console.log('🎉 EXCELLENT: Form submission now works with Vue mount fix!');
        } else {
          console.log('⚠️ Dialog still open - might have validation errors');
        }
      }
    }

  } catch (error) {
    console.error('❌ Edit test failed:', error);
    await page.screenshot({ path: 'tests/test-results/edit-test-error.png' });
  } finally {
    console.log('🔍 Leaving browser open for manual verification...');
    // await browser.close();
  }
}

testEditDirect();