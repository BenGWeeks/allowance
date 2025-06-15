const { chromium } = require('playwright');

async function run() {
  const browser = await chromium.launch({ 
    headless: false,
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });
  
  try {
    const context = await browser.newContext({
      viewport: { width: 1280, height: 1024 }
    });
    const page = await context.newPage();

    console.log('Starting button alignment screenshot test...');

    // Navigate to login page
    await page.goto('http://localhost:5000');
    console.log('Navigated to homepage');

    // Click on Login if create account form is shown
    try {
      const loginTab = await page.locator('[aria-label="Login"]').first();
      if (await loginTab.isVisible({ timeout: 3000 })) {
        await loginTab.click();
        console.log('Switched to Login tab');
        await page.waitForTimeout(1000);
      }
    } catch (e) {
      console.log('Login tab not found or already on login - continuing...');
    }

    // Login as admin
    await page.fill('[aria-label="Username"]', 'admin');
    await page.fill('[aria-label="Password"]', 'admin');
    console.log('Filled login credentials');

    await page.click('button[type="submit"]');
    console.log('Clicked login button');

    // Wait for successful login
    await page.waitForSelector('text=Add a new wallet', { timeout: 10000 });
    console.log('Successfully logged in');

    // Navigate to Extensions
    await page.click('text=Extensions');
    await page.waitForSelector('.q-card', { timeout: 5000 });
    console.log('Navigated to Extensions page');

    // Find and navigate to Allowance extension
    const allowanceCard = page.locator('.q-card:has(.text-h5:has-text("Allowance"))');
    const manageButton = allowanceCard.locator('button:has-text("Manage")');
    
    await manageButton.click();
    console.log('Clicked Manage on Allowance extension');

    // Wait for allowance page to load
    await page.waitForSelector('[data-cy="new-allowance-btn"]', { timeout: 10000 });
    console.log('Allowance extension page loaded');

    // Click "New Allowance" button to open the form
    await page.click('[data-cy="new-allowance-btn"]');
    console.log('Clicked New Allowance button');

    // Wait for dialog to appear
    await page.waitForSelector('.q-dialog', { timeout: 5000 });
    console.log('Dialog opened');

    // Fill in some form fields to show a realistic form state
    await page.fill('input[aria-label="Description *"]', 'Test allowance for button alignment');
    await page.selectOption('select[aria-label="Wallet *"]', { index: 0 });
    await page.fill('input[aria-label="Lightning Address *"]', 'test@example.com');
    await page.fill('input[aria-label="Amount *"]', '100');
    
    // Scroll to show the toggle and buttons
    await page.locator('label:has-text("Active")').scrollIntoViewIfNeeded();
    
    // Wait a moment for everything to settle
    await page.waitForTimeout(1000);

    // Take screenshot of the form showing the fixed button alignment
    await page.screenshot({ 
      path: 'tests/test-results/button-alignment-fixed.png',
      fullPage: false
    });
    console.log('Screenshot saved to tests/test-results/button-alignment-fixed.png');

    // Also take a screenshot focused on just the buttons area
    const buttonsArea = page.locator('.row.q-mt-lg');
    await buttonsArea.screenshot({
      path: 'tests/test-results/button-alignment-closeup.png'
    });
    console.log('Close-up screenshot saved to tests/test-results/button-alignment-closeup.png');

    console.log('✅ Button alignment screenshot test completed successfully');
    process.exit(0);

  } catch (error) {
    console.error('❌ Test failed:', error.message);
    
    // Take error screenshot
    try {
      await page.screenshot({ 
        path: 'tests/test-results/button-alignment-error.png',
        fullPage: true 
      });
      console.log('Error screenshot saved');
    } catch (screenshotError) {
      console.error('Failed to take error screenshot:', screenshotError.message);
    }
    
    process.exit(1);
  } finally {
    await browser.close();
  }
}

run();