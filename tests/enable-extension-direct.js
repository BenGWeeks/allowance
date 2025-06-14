const { chromium } = require('playwright');

async function enableExtensionDirect() {
  const browser = await chromium.launch({ headless: false });
  const context = await browser.newContext();
  const page = await context.newPage();

  try {
    console.log('🔧 Attempting to enable allowance extension...');
    
    // Go to LNBits
    await page.goto('http://localhost:5001/');
    await page.waitForLoadState('networkidle');
    
    console.log('📍 Current URL:', page.url());
    
    // Check if login screen exists
    const createAccountVisible = await page.locator('text=Create Account').first().isVisible();
    if (createAccountVisible) {
      console.log('🔄 Switching to login...');
      await page.click('text=Login');
      await page.waitForTimeout(2000);
    }
    
    // Login
    console.log('🔑 Logging in...');
    await page.fill('input[type="text"], input[type="email"]', 'ben.weeks');
    await page.fill('input[type="password"]', 'zUYmy&05&uZ$3kmf*^T8');
    await page.click('button:has-text("LOGIN")');
    await page.waitForTimeout(3000);

    console.log('📍 After login URL:', page.url());
    
    // Navigate to Extensions
    console.log('🧩 Navigating to Extensions...');
    await page.goto('http://localhost:5001/extensions');
    await page.waitForTimeout(3000);
    
    console.log('📍 Extensions page URL:', page.url());
    
    // Take screenshot for debugging
    await page.screenshot({ path: 'tests/test-results/extensions-page.png' });
    
    // Look for allowance extension
    const allowanceCard = page.locator('.q-card:has(.text-h5:has-text("Allowance"))');
    const cardExists = await allowanceCard.count() > 0;
    
    console.log('🎯 Allowance card found:', cardExists);
    
    if (cardExists) {
      const enableButton = allowanceCard.locator('button:has-text("Enable")');
      const enableExists = await enableButton.count() > 0;
      
      console.log('✅ Enable button found:', enableExists);
      
      if (enableExists) {
        await enableButton.click();
        await page.waitForTimeout(2000);
        console.log('🚀 Clicked Enable button');
        
        // Check if now shows Disable (success)
        const disableButton = allowanceCard.locator('button:has-text("Disable")');
        const disableExists = await disableButton.count() > 0;
        
        console.log('✅ Extension enabled (Disable button visible):', disableExists);
        
        if (disableExists) {
          console.log('🎯 Testing access to allowance extension...');
          await page.goto('http://localhost:5001/allowance');
          await page.waitForTimeout(3000);
          
          const newAllowanceButton = page.locator('button:has-text("New Allowance")');
          const buttonExists = await newAllowanceButton.count() > 0;
          
          console.log('✅ Allowance extension accessible:', buttonExists);
          console.log('📍 Final URL:', page.url());
          
          if (buttonExists) {
            console.log('🎉 SUCCESS: Extension enabled and accessible!');
          }
        }
      } else {
        const manageButton = allowanceCard.locator('button:has-text("Manage")');
        const manageExists = await manageButton.count() > 0;
        console.log('⚙️ Manage button found (already enabled):', manageExists);
        
        if (manageExists) {
          console.log('✅ Extension already enabled, testing access...');
          await page.goto('http://localhost:5001/allowance');
          await page.waitForTimeout(3000);
          
          const newAllowanceButton = page.locator('button:has-text("New Allowance")');
          const buttonExists = await newAllowanceButton.count() > 0;
          
          console.log('✅ Allowance extension accessible:', buttonExists);
          
          if (buttonExists) {
            console.log('🎉 SUCCESS: Extension already enabled and accessible!');
          }
        }
      }
    } else {
      console.log('❌ Allowance extension not found in extensions list');
      
      // Show available extensions
      const extensions = await page.locator('.q-card .text-h5').allTextContents();
      console.log('📋 Available extensions:', extensions);
    }

  } catch (error) {
    console.error('❌ Enable extension failed:', error);
    await page.screenshot({ path: 'tests/test-results/enable-extension-error.png' });
  } finally {
    await browser.close();
  }
}

enableExtensionDirect();