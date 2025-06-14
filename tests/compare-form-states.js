const { chromium } = require('playwright');

async function compareFormStates() {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext();
  const page = await context.newPage();

  try {
    console.log('🔬 Comparing form states between create and edit...');
    
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

    // Test 1: CREATE form state
    console.log('\n🧪 Test 1: CREATE form analysis');
    await page.click('button:has-text("New Allowance")');
    await page.waitForTimeout(2000);

    const createFormState = await page.evaluate(() => {
      const form = document.querySelector('form');
      const submitButton = document.querySelector('button[type="submit"]');
      
      return {
        formExists: !!form,
        formAction: form ? form.action : null,
        formMethod: form ? form.method : null,
        formOnSubmit: form ? !!form.onsubmit : false,
        formEventListeners: form ? Object.keys(form).filter(k => k.startsWith('on')) : [],
        submitButtonExists: !!submitButton,
        submitButtonText: submitButton ? submitButton.textContent.trim() : null,
        submitButtonType: submitButton ? submitButton.type : null,
        hasVueDirectives: form ? !!form.getAttribute('data-v-') || !!form.classList.toString().includes('vue') : false
      };
    });
    
    console.log('🟢 CREATE form state:', JSON.stringify(createFormState, null, 2));

    // Fill minimal form data
    await page.fill('input[placeholder*="Weekly allowance"]', 'Test Create');
    await page.fill('input[placeholder*="alice@getalby.com"]', 'test@example.com');
    await page.fill('input[type="number"]', '50');

    // Check form validity before submission
    const createFormValidity = await page.evaluate(() => {
      const form = document.querySelector('form');
      return {
        formValid: form ? form.checkValidity() : false,
        requiredFields: Array.from(document.querySelectorAll('input[required], select[required]')).map(el => ({
          type: el.type,
          value: el.value,
          valid: el.checkValidity(),
          validationMessage: el.validationMessage
        }))
      };
    });
    
    console.log('🟢 CREATE form validity:', JSON.stringify(createFormValidity, null, 2));

    // Close create dialog
    await page.click('button:has-text("Cancel")');
    await page.waitForTimeout(1000);

    // Test 2: EDIT form state
    console.log('\n🧪 Test 2: EDIT form analysis');
    const firstRow = page.locator('.q-table tbody tr').first();
    const editButton = firstRow.locator('button.text-light-blue');
    await editButton.click();
    await page.waitForTimeout(2000);

    const editFormState = await page.evaluate(() => {
      const form = document.querySelector('form');
      const submitButton = document.querySelector('button[type="submit"]');
      
      return {
        formExists: !!form,
        formAction: form ? form.action : null,
        formMethod: form ? form.method : null,
        formOnSubmit: form ? !!form.onsubmit : false,
        formEventListeners: form ? Object.keys(form).filter(k => k.startsWith('on')) : [],
        submitButtonExists: !!submitButton,
        submitButtonText: submitButton ? submitButton.textContent.trim() : null,
        submitButtonType: submitButton ? submitButton.type : null,
        hasVueDirectives: form ? !!form.getAttribute('data-v-') || !!form.classList.toString().includes('vue') : false
      };
    });
    
    console.log('🔴 EDIT form state:', JSON.stringify(editFormState, null, 2));

    // Check form validity 
    const editFormValidity = await page.evaluate(() => {
      const form = document.querySelector('form');
      return {
        formValid: form ? form.checkValidity() : false,
        requiredFields: Array.from(document.querySelectorAll('input[required], select[required]')).map(el => ({
          type: el.type,
          value: el.value,
          valid: el.checkValidity(),
          validationMessage: el.validationMessage
        }))
      };
    });
    
    console.log('🔴 EDIT form validity:', JSON.stringify(editFormValidity, null, 2));

    // Compare differences
    console.log('\n📊 Key Differences:');
    const differences = [];
    
    if (createFormState.submitButtonText !== editFormState.submitButtonText) {
      differences.push(`Button text: "${createFormState.submitButtonText}" vs "${editFormState.submitButtonText}"`);
    }
    
    if (createFormValidity.formValid !== editFormValidity.formValid) {
      differences.push(`Form validity: ${createFormValidity.formValid} vs ${editFormValidity.formValid}`);
    }

    const createInvalidFields = createFormValidity.requiredFields.filter(f => !f.valid);
    const editInvalidFields = editFormValidity.requiredFields.filter(f => !f.valid);
    
    if (createInvalidFields.length !== editInvalidFields.length) {
      differences.push(`Invalid fields count: ${createInvalidFields.length} vs ${editInvalidFields.length}`);
    }

    if (differences.length > 0) {
      differences.forEach(diff => console.log(`  • ${diff}`));
    } else {
      console.log('  No significant differences found');
    }

    // Show invalid fields for edit
    if (editInvalidFields.length > 0) {
      console.log('\n❌ Invalid fields in EDIT form:');
      editInvalidFields.forEach(field => {
        console.log(`  • ${field.type}: "${field.value}" - ${field.validationMessage}`);
      });
    }

  } catch (error) {
    console.error('❌ Form comparison failed:', error);
  } finally {
    await browser.close();
  }
}

compareFormStates();