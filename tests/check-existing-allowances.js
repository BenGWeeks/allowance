const { chromium } = require('playwright');

async function checkExistingAllowances() {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext();
  const page = await context.newPage();

  try {
    console.log('🔍 Checking for existing allowances...');
    
    // Capture the GET request to see if there are existing allowances
    let allowancesData = null;
    page.on('response', async response => {
      if (response.url().includes('/allowance/api/v1/allowance') && response.request().method() === 'GET') {
        try {
          const data = await response.json();
          allowancesData = data;
          console.log(`📥 Found ${data.length} existing allowances`);
          if (data.length > 0) {
            console.log('📋 Existing allowances:');
            data.forEach((allowance, i) => {
              console.log(`  ${i + 1}. "${allowance.name}" - ${allowance.amount} ${allowance.currency} ${allowance.frequency_type}`);
              console.log(`      Created: ${allowance.created_at || 'Unknown'}`);
              console.log(`      Active: ${allowance.active}`);
            });
          }
        } catch (e) {
          console.log('📥 Error parsing allowances data:', e.message);
        }
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

    // Navigate to allowance page to trigger the GET request
    await page.goto('http://localhost:5001/allowance');
    await page.waitForTimeout(3000);
    
    // Check what's actually displayed in the table
    const tableContent = await page.evaluate(() => {
      const table = document.querySelector('.q-table');
      if (!table) return 'No table found';
      
      const rows = table.querySelectorAll('tbody tr');
      if (rows.length === 0) return 'Table found but no rows';
      
      const allowances = [];
      rows.forEach(row => {
        const cells = row.querySelectorAll('td');
        if (cells.length > 0) {
          allowances.push({
            id: cells[0]?.textContent?.trim() || '',
            name: cells[1]?.textContent?.trim() || '',
            amount: cells[2]?.textContent?.trim() || '',
            recipient: cells[3]?.textContent?.trim() || '',
            frequency: cells[4]?.textContent?.trim() || '',
            status: cells[5]?.textContent?.trim() || ''
          });
        }
      });
      
      return allowances;
    });
    
    console.log('\n🔍 Table display check:');
    if (typeof tableContent === 'string') {
      console.log(`❌ ${tableContent}`);
    } else if (tableContent.length === 0) {
      console.log('✅ Table exists but empty');
    } else {
      console.log(`✅ Table shows ${tableContent.length} allowances:`);
      tableContent.forEach((allowance, i) => {
        console.log(`  ${i + 1}. ${allowance.name} - ${allowance.amount} to ${allowance.recipient}`);
      });
    }
    
    // Test if we can click on an edit button (if any exist)
    const editButtons = await page.locator('button.text-light-blue').count();
    console.log(`\n🔧 Edit buttons found: ${editButtons}`);
    
    if (editButtons > 0) {
      console.log('🧪 Testing edit button click...');
      
      // Click the first edit button
      await page.locator('button.text-light-blue').first().click();
      await page.waitForTimeout(2000);
      
      const dialogVisible = await page.locator('.q-dialog').isVisible();
      console.log('📋 Edit dialog opened:', dialogVisible);
      
      if (dialogVisible) {
        // Check what data is pre-filled
        const formData = await page.evaluate(() => {
          const inputs = document.querySelectorAll('.q-dialog input, .q-dialog select');
          const data = {};
          inputs.forEach(input => {
            if (input.placeholder) {
              data[input.placeholder] = input.value;
            } else if (input.getAttribute('aria-label')) {
              data[input.getAttribute('aria-label')] = input.value;
            }
          });
          return data;
        });
        
        console.log('📝 Pre-filled form data:', JSON.stringify(formData, null, 2));
        
        // Check the active toggle state
        const toggleState = await page.evaluate(() => {
          const toggle = document.querySelector('.q-dialog .q-toggle');
          if (toggle) {
            const input = toggle.querySelector('input[type="checkbox"]');
            return {
              exists: true,
              checked: input ? input.checked : false,
              ariaChecked: toggle.getAttribute('aria-checked')
            };
          }
          return { exists: false };
        });
        
        console.log('🔘 Toggle state:', toggleState);
      }
    }

  } catch (error) {
    console.error('❌ Check failed:', error);
  } finally {
    await browser.close();
  }
}

checkExistingAllowances();