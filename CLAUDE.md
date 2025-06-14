- You can reference the best practice implementation at https://github.com/lnbits/myextension (although the documentation on there might not be up-to-date)

## LNBits Extension Development Learnings

### Vue.js Integration Issues (RESOLVED)
1. **localStorage Error**: The persistent `Cannot read properties of undefined (reading 'localStorage')` error comes from LNBits' bundle.min.js, specifically when windowMixin tries to access `this.$q.localStorage` during Vue app initialization.
   - **Solution**: Follow LNURLP pattern exactly - use `el: '#vue'` WITHOUT `.mount('#vue')` call

2. **Vue 3 vs Vue 2**: LNBits uses Vue 3 (confirmed by "Vue is not a constructor" error when trying Vue 2 syntax).

3. **App Mounting**: LNBits has an automatic mounting system. Do NOT call `.mount('#vue')` manually.
   - **Correct Pattern**: 
   ```javascript
   window.app = Vue.createApp({
     el: '#vue',
     mixins: [window.windowMixin],
     // ... rest of app
   })  // NO .mount() call!
   ```

4. **windowMixin Required**: The windowMixin is essential for LNBits extensions - it provides access to user data, wallets, and Quasar utilities.

### Form Submission Issues (RESOLVED)
1. **@submit.prevent vs @click**: Use `@click="saveAllowance"` on the submit button instead of form @submit
   - **Working Pattern**: `<q-btn @click="saveAllowance">Create Allowance</q-btn>`

2. **Validation Blocking**: Missing required fields cause silent validation failures
   - **Solution**: Always provide default values for required fields in `openCreateDialog()`
   - **Critical Fix**: Default `frequency_type` was missing, causing all submissions to fail

3. **Edit Form Issues**: 
   - **Problem**: Clicking "Update Allowance" would only toggle Active state instead of saving
   - **Root Cause**: Missing `start_date` field in form data mapping
   - **Solution**: Ensure all fields are properly mapped in `openUpdateDialog()`

### Testing Suite
The extension includes comprehensive Playwright test scripts in `/tests/`:

#### Test Scripts
- **create-admin-account.js** - Creates initial superuser account on fresh LNBits install
  - Detects "Set up the Superuser account below." screen
  - Fills credentials using aria-label selectors
  - Confirms success by finding "Add a new wallet" text
  
- **login-test.js** - Tests admin login functionality
  - Handles switching from "Create Account" to Login screen
  - Tests with actual admin credentials
  - Confirms success with "Add a new wallet" visibility
  
- **enable-allowance.js** - Enables the allowance extension
  - Navigates to Extensions page
  - Finds Allowance card specifically
  - Clicks Enable button (not Manage)
  - Confirms success by checking for "Disable" button
  
- **create-allowance.js** - End-to-end allowance creation test
  - Logs in, navigates to extension, creates allowance
  - Uses proper form selectors and waits
  - Verifies allowance appears in table
  
- **run_test.sh** - Test orchestration script
  - Runs all tests in sequence
  - Proper exit codes for CI/CD integration
  - Screenshots saved to `tests/test-results/`

#### Test Naming Conventions
- Use descriptive action-based names (create-allowance.js, not step1.js)
- Single-purpose scripts with clear goals
- Chain scripts by calling previous scripts when needed

#### Selector Best Practices
- Use aria-label attributes for form inputs: `[aria-label="Username"]`
- Check for specific text within cards: `.q-card:has(.text-h5:has-text("Allowance"))`
- Handle multiple elements with `.first()` or specific targeting
- Confirm state changes with button text (Enable → Disable)

### Current Status
✅ All core functionality working:
- Admin account creation and login
- Extension enabling via UI
- Allowance creation through forms (POST requests successful)
- Allowance editing through forms (PUT requests successful)
- Proper error handling and exit codes
- Vue app mounting following LNURLP pattern
- Form validation with required field defaults

### Git Best Practices
- Don't commit broken code - use `git stash` instead
- Name test files descriptively following action-based conventions
- All tests use proper exit codes (0 for success, 1 for failure)

- When looking for best practice of how to create an extension, look at https://github.com/lnbits/lnbits/tree/main/lnbits/extensions/lnurlp (do not download it, just look at the source)