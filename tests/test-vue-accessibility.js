const { chromium } = require('playwright');

async function testVueAccessibility() {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext();
  const page = await context.newPage();

  try {
    console.log('🔬 Testing Vue accessibility during create vs edit...');
    
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

    // Test 1: Vue accessibility during CREATE
    console.log('\n🧪 Test 1: CREATE form Vue accessibility');
    await page.click('button:has-text("New Allowance")');
    await page.waitForTimeout(2000);

    const createVueState = await page.evaluate(() => {
      const results = [];
      
      // Check different Vue access methods
      const vueEl = document.querySelector('#vue');
      if (vueEl && vueEl.__vue_app__) {
        const app = vueEl.__vue_app__;
        if (app._instance && app._instance.ctx && app._instance.ctx.saveAllowance) {
          results.push('✅ saveAllowance found in Vue context');
        } else {
          results.push('❌ saveAllowance NOT found in Vue context');
        }
      }

      // Check window.app
      if (window.app && typeof window.app.saveAllowance === 'function') {
        results.push('✅ saveAllowance found in window.app');
      } else {
        results.push('❌ saveAllowance NOT found in window.app');
      }

      // Check form element for Vue component
      const form = document.querySelector('form');
      if (form && form.__vue__) {
        results.push('✅ Vue component found on form element');
      } else {
        results.push('❌ No Vue component on form element');
      }

      return results.join(' | ');
    });
    console.log('🟢 CREATE Vue state:', createVueState);

    // Close create dialog
    await page.click('button:has-text("Cancel")');
    await page.waitForTimeout(1000);

    // Test 2: Vue accessibility during EDIT
    console.log('\n🧪 Test 2: EDIT form Vue accessibility');
    const firstRow = page.locator('.q-table tbody tr').first();
    const editButton = firstRow.locator('button.text-light-blue');
    await editButton.click();
    await page.waitForTimeout(2000);

    const editVueState = await page.evaluate(() => {
      const results = [];
      
      // Check different Vue access methods
      const vueEl = document.querySelector('#vue');
      if (vueEl && vueEl.__vue_app__) {
        const app = vueEl.__vue_app__;
        if (app._instance && app._instance.ctx && app._instance.ctx.saveAllowance) {
          results.push('✅ saveAllowance found in Vue context');
        } else {
          results.push('❌ saveAllowance NOT found in Vue context');
        }
      }

      // Check window.app
      if (window.app && typeof window.app.saveAllowance === 'function') {
        results.push('✅ saveAllowance found in window.app');
      } else {
        results.push('❌ saveAllowance NOT found in window.app');
      }

      // Check form element for Vue component
      const form = document.querySelector('form');
      if (form && form.__vue__) {
        results.push('✅ Vue component found on form element');
        if (form.__vue__.saveAllowance) {
          results.push('✅ saveAllowance found on form Vue component');
        } else {
          results.push('❌ saveAllowance NOT found on form Vue component');
        }
      } else {
        results.push('❌ No Vue component on form element');
      }

      return results.join(' | ');
    });
    console.log('🔴 EDIT Vue state:', editVueState);

    // Test 3: Try to manually call saveAllowance during edit
    console.log('\n🧪 Test 3: Manual saveAllowance call during EDIT');
    const manualCallResult = await page.evaluate(() => {
      // Try different ways to call saveAllowance
      const vueEl = document.querySelector('#vue');
      if (vueEl && vueEl.__vue_app__ && vueEl.__vue_app__._instance && vueEl.__vue_app__._instance.ctx) {
        const ctx = vueEl.__vue_app__._instance.ctx;
        if (typeof ctx.saveAllowance === 'function') {
          try {
            console.log('🔥 Calling saveAllowance from Vue context...');
            ctx.saveAllowance();
            return 'Successfully called saveAllowance from Vue context';
          } catch (error) {
            return `Error calling saveAllowance: ${error.message}`;
          }
        }
      }
      return 'Could not find or call saveAllowance';
    });
    console.log('🧪 Manual call result:', manualCallResult);

    await page.waitForTimeout(2000);

  } catch (error) {
    console.error('❌ Vue accessibility test failed:', error);
  } finally {
    await browser.close();
  }
}

testVueAccessibility();