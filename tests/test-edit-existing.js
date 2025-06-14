const { chromium } = require('playwright');

async function testEditExisting() {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext();
  const page = await context.newPage();

  try {
    console.log('🧪 Testing edit functionality with existing allowance...');
    
    // Capture network requests
    const requests = [];
    page.on('request', request => {
      if (request.url().includes('/allowance/api/v1/')) {
        requests.push({
          method: request.method(),
          url: request.url(),
          data: request.postData()
        });
        console.log(`📡 ${request.method()} ${request.url()}`);
      }
    });

    page.on('response', response => {
      if (response.url().includes('/allowance/api/v1/')) {
        console.log(`📥 ${response.status()} ${response.url()}`);
      }
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

    await page.goto('http://localhost:5001/allowance');
    await page.waitForTimeout(3000);
    
    // Click edit on the first allowance
    console.log('🔧 Clicking edit button on first allowance...');
    await page.locator('button.text-light-blue').first().click();
    await page.waitForTimeout(2000);
    
    const dialogVisible = await page.locator('.q-dialog').isVisible();
    console.log('📋 Edit dialog opened:', dialogVisible);
    
    if (dialogVisible) {
      // Check current toggle state
      const initialToggleState = await page.evaluate(() => {
        const toggle = document.querySelector('.q-dialog .q-toggle');
        if (toggle) {
          const input = toggle.querySelector('input[type="checkbox"]');
          return {
            checked: input ? input.checked : false,
            ariaChecked: toggle.getAttribute('aria-checked'),
            value: toggle.__vue__ ? toggle.__vue__.value : 'No Vue data'
          };
        }
        return null;
      });
      
      console.log('🔘 Initial toggle state:', initialToggleState);
      
      // Make a small change to test if edit works
      console.log('📝 Making small edit to amount...');
      await page.fill('input[type="number"]', '125');  // Change from 100 to 125
      
      // Check Vue app state before submission
      const vueStateBeforeSubmit = await page.evaluate(() => {
        return {
          windowApp: typeof window.app !== 'undefined',
          saveAllowanceExists: window.app && typeof window.app.saveAllowance === 'function',
          formDialogShow: window.app && window.app.formDialog ? window.app.formDialog.show : 'Not accessible'
        };
      });
      
      console.log('🔍 Vue state before submit:', vueStateBeforeSubmit);
      
      console.log('🚀 Clicking Update Allowance button...');
      await page.click('button[type="submit"]');
      
      // Wait for response
      await page.waitForTimeout(5000);
      
      const dialogClosed = !await page.locator('.q-dialog').isVisible();
      console.log('📋 Dialog closed after submit:', dialogClosed);
      
      const putRequests = requests.filter(r => r.method === 'PUT');
      console.log(`📊 PUT requests made: ${putRequests.length}`);
      
      if (putRequests.length > 0) {
        console.log('✅ PUT request was made! Edit functionality IS working');
        putRequests.forEach((req, i) => {
          console.log(`  ${i + 1}. ${req.method} ${req.url}`);
          if (req.data) {
            console.log(`     Data: ${req.data.substring(0, 200)}...`);
          }
        });
      } else {
        console.log('❌ No PUT request made - edit submission failed');
        
        // Check if there are validation errors
        const validationErrors = await page.evaluate(() => {
          const errorElements = document.querySelectorAll('.q-field--error, .text-negative');
          return Array.from(errorElements).map(el => el.textContent.trim()).filter(text => text);
        });
        
        if (validationErrors.length > 0) {
          console.log('⚠️ Validation errors found:');
          validationErrors.forEach(error => console.log(`  - ${error}`));
        }
      }
      
      // Final toggle state check
      const finalToggleState = await page.evaluate(() => {
        const toggle = document.querySelector('.q-dialog .q-toggle');
        if (toggle) {
          const input = toggle.querySelector('input[type="checkbox"]');
          return {
            checked: input ? input.checked : false,
            ariaChecked: toggle.getAttribute('aria-checked')
          };
        }
        return null;
      });
      
      console.log('🔘 Final toggle state:', finalToggleState);
      
      if (initialToggleState && finalToggleState) {
        if (initialToggleState.checked !== finalToggleState.checked) {
          console.log('⚠️ TOGGLE STATE CHANGED during submission!');
        }
      }
    }

  } catch (error) {
    console.error('❌ Edit test failed:', error);
  } finally {
    await browser.close();
  }
}

testEditExisting();