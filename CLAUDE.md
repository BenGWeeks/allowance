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

### Repository Structure
The repository follows a clean structure with proper .gitignore patterns:

```
allowance/
├── tests/                    # Playwright test scripts
│   ├── create-admin-account.js
│   ├── login-test.js
│   ├── enable-allowance.js
│   ├── create-allowance.js
│   ├── run_test.sh
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

### Code Quality and CI/CD

#### Local Testing Before Push
Before pushing changes, always run local tests to ensure CI will pass:

```bash
# Create virtual environment for testing
python3 -m venv .test-venv
source .test-venv/bin/activate

# Install linting tools
pip install black mypy ruff pydantic fastapi

# Run all checks
echo "=== BLACK CHECK ===" && black --check *.py
echo "=== RUFF CHECK ===" && ruff check *.py
echo "=== MYPY CHECK ===" && mypy --ignore-missing-imports *.py

# Clean up
rm -rf .test-venv
```

#### GitHub Actions CI Pipeline
The repository includes comprehensive CI checks:
- **Black**: Code formatting validation (88 character line length)
- **Ruff**: Modern Python linting with import organization
- **MyPy**: Static type checking for better code quality
- **Pyright**: Additional type checking
- **Bundle/Prettier**: JavaScript/CSS formatting checks

#### Common CI Issues and Solutions

1. **Dependency Conflicts**: 
   - Issue: Poetry dependency resolution fails with psycopg2-binary version conflicts
   - Solution: Use Python constraint `">=3.9,<3.13"` in pyproject.toml
   - Remove poetry.lock to force fresh dependency resolution

2. **Type Annotation Errors**:
   - Use `list[Type]` instead of `typing.List[Type]` for Python 3.9+
   - Convert objects properly: `CreateAllowanceData(**allowance.dict())` for updates
   - Add proper type hints to function parameters

3. **Import Organization**:
   - Ruff automatically fixes import ordering with `ruff check --fix`
   - Remove unused imports to pass linting

4. **Line Length**:
   - Black enforces 88 character line limit
   - Split long strings across multiple lines when needed

#### Acceptable Warnings
- **C901 Complexity Warning**: Background task functions can exceed complexity limits
- This warning doesn't fail CI but indicates function could be refactored

### Development Environment
- Make sure you are working on the dev docker of lnbits (running on port 5001), not the production version (running on port 5000)
- When looking for best practice of how to create an extension, look at https://github.com/lnbits/lnbits/tree/main/lnbits/extensions/lnurlp (do not download it, just look at the source)