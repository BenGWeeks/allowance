const { chromium } = require('playwright');

async function testMinimalForm() {
  const browser = await chromium.launch({ headless: false });
  const context = await browser.newContext();
  const page = await context.newPage();

  try {
    console.log('🧪 Testing minimal form without windowMixin...');
    
    // Capture console logs
    page.on('console', msg => {
      console.log(`📣 ${msg.type()}: ${msg.text()}`);
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

    console.log('🎯 Navigating to minimal test page...');
    await page.goto('http://localhost:5001/allowance/test-minimal');
    await page.waitForTimeout(3000);
    
    console.log('📍 Current URL:', page.url());
    
    // Check if the test button exists
    const testButton = page.locator('button:has-text("Test Minimal Form")');
    const buttonExists = await testButton.count() > 0;
    
    console.log('✅ Test button found:', buttonExists);
    
    if (buttonExists) {
      console.log('🔄 Clicking test button...');
      await testButton.click();
      await page.waitForTimeout(2000);
      
      // Check if dialog opened
      const dialog = page.locator('.q-dialog');
      const dialogVisible = await dialog.isVisible();
      console.log('✅ Dialog opened:', dialogVisible);
      
      if (dialogVisible) {
        console.log('📝 Filling form...');
        await page.fill('input[label="Description *"]', 'Test Description');
        await page.fill('input[type="number"]', '100');
        
        console.log('🚀 Submitting form...');
        await page.click('button[type="submit"]');
        
        // Wait and check if dialog closed
        await page.waitForTimeout(3000);
        const dialogClosed = !await dialog.isVisible();
        console.log('✅ Dialog closed (success):', dialogClosed);
        
        if (dialogClosed) {
          console.log('🎉 SUCCESS: Minimal form submission works!');
        } else {
          console.log('❌ Dialog still open - form submission failed');
        }
      }
    } else {
      console.log('❌ Test button not found');
      const pageContent = await page.textContent('body');
      console.log('📄 Page content preview:', pageContent.substring(0, 200));
    }

  } catch (error) {
    console.error('❌ Minimal form test failed:', error);
    await page.screenshot({ path: 'tests/test-results/minimal-form-error.png' });
  } finally {
    console.log('🔍 Browser left open for inspection...');
    // Don't close for manual inspection
    // await browser.close();
  }
}

testMinimalForm();