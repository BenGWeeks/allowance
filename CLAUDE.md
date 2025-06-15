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
The extension includes comprehensive test suites for both API and UI testing:

#### Test Organization
- **API Tests**: `/tests/api_*.py` - Python-based API endpoint testing
- **UI Tests**: `/tests/ui_*.js` - Playwright browser automation testing
- **Test Runners**: Shell scripts to orchestrate all testing

#### Test Scripts
**UI Tests (Playwright):**
- **ui_create_admin_account.js** - Creates initial superuser account on fresh LNBits install
- **ui_login_test.js** - Tests admin login functionality
- **ui_enable_allowance.js** - Enables the allowance extension via UI
- **ui_create_allowance.js** - End-to-end allowance creation test
- **ui_edit_allowance.js** - Tests allowance editing through forms
- **ui_delete_allowance.js** - Tests allowance deletion functionality

**API Tests (Python):**
- **api_allowances.py** - Tests core allowance CRUD API endpoints

**Test Runners:**
- **run_all_tests.sh** - Runs both API and UI tests in sequence
- **run_api_tests.sh** - Runs only API tests (Python)
- **run_ui_tests.sh** - Runs only UI tests (Playwright)

#### Test Naming Conventions
- **API Tests**: `api_*.py` - Python files for testing API endpoints
- **UI Tests**: `ui_*.js` - JavaScript files for testing user interface
- Use descriptive action-based names (ui_create_allowance.js, not step1.js)
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

### Repository Structure
The repository follows a clean structure with proper .gitignore patterns:

```
allowance/
├── tests/                    # Comprehensive test suite
│   ├── api_*.py             # API endpoint tests (Python)
│   ├── ui_*.js              # UI automation tests (Playwright)
│   ├── run_all_tests.sh     # Run all tests
│   ├── run_api_tests.sh     # Run API tests only
│   ├── run_ui_tests.sh      # Run UI tests only
│   └── test-results/        # Generated screenshots (ignored)
├── static/js/               # Vue.js frontend
├── templates/allowance/     # HTML templates
├── crud.py                  # Database operations
├── views.py                 # Frontend routes
├── views_api.py            # API endpoints
└── manifest.json           # Extension manifest
```

### Git Best Practices
- Don't commit broken code - use `git stash` instead
- Name test files descriptively following action-based conventions
- All tests use proper exit codes (0 for success, 1 for failure)
- Repository excludes temporary files (data/, temp/, test results, screenshots)
- Clean commit history with descriptive messages

### API Authentication Fix
Fixed critical authentication issue in `views_api.py`:
- Changed `wallet.id` to `wallet.wallet.id` for proper wallet ID access
- Fixed 403 Forbidden errors when creating/editing allowances
- Improved delete endpoint to return proper JSON response

### Code Quality and Testing

#### Local Development Testing (Optional)
For development quality checks, you can run local linting (but this is not required for CI):

```bash
# Optional: Quick quality check during development
python3 -m venv .test-venv
source .test-venv/bin/activate
pip install black mypy ruff pydantic fastapi

# Run checks
black --check *.py && ruff check *.py && mypy --ignore-missing-imports *.py

# Clean up
rm -rf .test-venv
```

#### GitHub Actions Testing
Following LNBits extension best practices, we focus on **functional testing** rather than heavy linting:

- **Functional Tests**: End-to-end extension testing with real LNBits environment
- **Integration Tests**: Full Playwright browser automation testing
- **Database Tests**: PostgreSQL integration with actual extension workflows

**Philosophy**: *"The easier an extension is to review, the quicker the review process"* - LNBits Guidelines

#### Extension Development Approach
Following LNBits extension guidelines:
- ✅ **Submit fully working extensions**
- ✅ **Minimize dependencies** 
- ✅ **Keep it simple and reviewable**
- ✅ **Focus on functionality over tooling**

### Development Environment
- Make sure you are working on the dev docker of lnbits (running on port 5001), not the production version (running on port 5000)
- When looking for best practice of how to create an extension, look at https://github.com/lnbits/lnbits/tree/main/lnbits/extensions/lnurlp (do not download it, just look at the source)