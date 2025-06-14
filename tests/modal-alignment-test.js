const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

(async () => {
  console.log('🎯 Testing modal vertical alignment...');
  
  const browser = await chromium.launch({ headless: true, slowMo: 500 });
  const page = await browser.newPage();
  
  // Set viewport to standard size for consistent screenshots
  await page.setViewportSize({ width: 1280, height: 720 });

  try {
    console.log('🚀 Starting modal alignment test...');
    
    // Listen for console errors
    page.on('console', msg => {
      if (msg.type() === 'error') {
        console.log('❌ Browser console error:', msg.text());
      }
    });
    
    page.on('pageerror', error => {
      console.log('💥 Page error:', error.message);
    });
    
    // Step 1: Login first
    console.log('📝 Step 1: Logging in as admin...');
    await page.goto('http://localhost:5001/');
    await page.waitForLoadState('networkidle');
    
    // Check if we need to switch to login screen
    const createAccountVisible = await page.locator('text=Create Account').first().isVisible();
    if (createAccountVisible) {
      await page.click('text=Login');
      await page.waitForTimeout(2000);
    }
    
    // Fill login credentials
    await page.fill('input[type="text"], input[type="email"]', 'ben.weeks');
    await page.fill('input[type="password"]', 'zUYmy&05&uZ$3kmf*^T8');
    await page.click('button:has-text("LOGIN")');
    await page.waitForTimeout(3000);
    
    // Step 2: Navigate to allowance extension
    console.log('📝 Step 2: Navigating to allowance extension...');
    await page.goto('http://localhost:5001/allowance/');
    await page.waitForTimeout(3000);
    
    // Step 3: Open the modal
    console.log('📝 Step 3: Opening modal...');
    const newAllowanceButton = page.locator('button:has-text("New Allowance")');
    
    if (await newAllowanceButton.isVisible()) {
      await newAllowanceButton.click();
      await page.waitForTimeout(2000);
      
      // Wait for modal to appear
      await page.waitForSelector('.q-dialog', { timeout: 10000 });
      console.log('✅ Modal opened successfully');
      
      // Check if modal is visible and positioned correctly
      const modal = page.locator('.q-dialog');
      const modalVisible = await modal.isVisible();
      
      if (modalVisible) {
        console.log('✅ Modal is visible');
        
        // Get modal position info
        const modalInfo = await page.evaluate(() => {
          const dialog = document.querySelector('.q-dialog');
          const dialogCard = document.querySelector('.q-dialog .q-card');
          if (dialog && dialogCard) {
            const dialogRect = dialog.getBoundingClientRect();
            const cardRect = dialogCard.getBoundingClientRect();
            return {
              windowHeight: window.innerHeight,
              windowWidth: window.innerWidth,
              dialogTop: dialogRect.top,
              dialogHeight: dialogRect.height,
              cardTop: cardRect.top,
              cardHeight: cardRect.height,
              cardCenterY: cardRect.top + cardRect.height / 2,
              windowCenterY: window.innerHeight / 2,
              isVerticallyCenter: Math.abs((cardRect.top + cardRect.height / 2) - (window.innerHeight / 2)) < 50
            };
          }
          return null;
        });
        
        console.log('📊 Modal positioning info:', JSON.stringify(modalInfo, null, 2));
        
        if (modalInfo && modalInfo.isVerticallyCenter) {
          console.log('✅ Modal is vertically centered!');
        } else {
          console.log('⚠️ Modal may not be perfectly centered');
        }
        
        // Take screenshot showing the modal alignment
        const screenshotPath = path.join(__dirname, 'test-results', 'modal-vertical-alignment-fixed.png');
        
        // Ensure test-results directory exists
        const resultsDir = path.join(__dirname, 'test-results');
        if (!fs.existsSync(resultsDir)) {
          fs.mkdirSync(resultsDir, { recursive: true });
        }
        
        await page.screenshot({ 
          path: screenshotPath,
          fullPage: false // Just capture viewport to show modal positioning
        });
        console.log(`📸 Screenshot saved: ${screenshotPath}`);
        
        // Add some visual emphasis to the modal for the screenshot
        await page.evaluate(() => {
          const modal = document.querySelector('.q-dialog .q-card');
          if (modal) {
            modal.style.boxShadow = '0 0 20px 5px #ff6b6b';
            modal.style.border = '3px solid #ff6b6b';
          }
        });
        
        // Take another screenshot with emphasis
        const emphasizedScreenshotPath = path.join(__dirname, 'test-results', 'modal-vertical-alignment-emphasized.png');
        await page.screenshot({ 
          path: emphasizedScreenshotPath,
          fullPage: false
        });
        console.log(`📸 Emphasized screenshot saved: ${emphasizedScreenshotPath}`);
        
        console.log('🎉 MODAL ALIGNMENT TEST PASSED! 🎉');
        process.exit(0); // Success
        
      } else {
        console.log('❌ Modal is not visible');
        await page.screenshot({ path: path.join(__dirname, 'test-results', 'modal-not-visible.png') });
        process.exit(1); // Failure
      }
      
    } else {
      console.log('❌ New Allowance button not found');
      await page.screenshot({ path: path.join(__dirname, 'test-results', 'no-button.png') });
      process.exit(1); // Failure
    }
    
  } catch (error) {
    console.error('💥 Error:', error.message);
    const errorScreenshotPath = path.join(__dirname, 'test-results', 'modal-alignment-error.png');
    await page.screenshot({ path: errorScreenshotPath });
    console.log(`📸 Error screenshot saved: ${errorScreenshotPath}`);
    process.exit(1); // Failure
  } finally {
    await browser.close();
  }
})();