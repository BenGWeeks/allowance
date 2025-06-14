- You can reference the best practice implementation at https://github.com/lnbits/myextension (although the documentation on there might not be up-to-date)

## LNBits Extension Development Learnings

### Vue.js Integration Issues
1. **localStorage Error**: The persistent `Cannot read properties of undefined (reading 'localStorage')` error comes from LNBits' bundle.min.js, specifically when windowMixin tries to access `this.$q.localStorage` during Vue app initialization.

2. **Vue 3 vs Vue 2**: LNBits uses Vue 3 (confirmed by "Vue is not a constructor" error when trying Vue 2 syntax).

3. **App Mounting**: The Vue app must be mounted with `.mount('#vue')` - without this, the form submission handlers don't work.

4. **windowMixin Required**: The windowMixin is essential for LNBits extensions - it provides access to user data, wallets, and Quasar utilities.

### Form Submission Issues
1. **@submit.prevent Required**: Quasar forms need `@submit.prevent="saveAllowance"` to prevent default form submission.

2. **Validation Blocking**: Empty validation errors `[ '', '', '', '', '', '' ]` suggest Quasar validation is blocking form submission but not providing proper error messages.

3. **Active Toggle Issue**: The Active toggle mysteriously switches to OFF when the form is submitted, indicating potential data binding issues.

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
- Allowance creation through forms
- Proper error handling and exit codes

### Git Best Practices
- Don't commit broken code - use `git stash` instead
- Name test files descriptively following action-based conventions
- All tests use proper exit codes (0 for success, 1 for failure)

- When looking for best practice of how to create an extension, look at https://github.com/lnbits/lnbits/tree/main/lnbits/extensions/lnurlp (do not download it, just look at the source)

### Development Environment
- Make sure you are working on the dev docker of lnbits (running on port 5001), not the production version (running on port 5000).