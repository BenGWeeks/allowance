- You can reference the best practice implementation at https://github.com/lnbits/myextension (although the documentation on there might not be up-to-date)

## Environment Configuration

### NEVER Hardcode Credentials
- **Always use .env.local** for sensitive configuration:
  - `TEST_LNBITS_URL` - The LNBits instance URL (e.g., http://localhost:5001)
  - `LNBITS_ADMIN_USERNAME` - Admin username for authentication
  - `LNBITS_ADMIN_PASSWORD` - Admin password for authentication
  - `RECEIVING_WALLET_NAME` - Name for the receiving wallet
  - `PAYLINK_EMAIL` - Email address for PayLinks

### Example .env.local:
```
TEST_LNBITS_URL=http://localhost:5001
LNBITS_ADMIN_USERNAME=ben.weeks
LNBITS_ADMIN_PASSWORD=zUYmy&05&uZ$3kmf*^T8
RECEIVING_WALLET_NAME=Receiving
PAYLINK_EMAIL=receiving@lnbits-allowance.weeksfamily.me
```

### Loading Environment Variables:
**ALL test scripts MUST use the `auth-helper.js` module** which properly loads from .env.local:
```javascript
const { getConfig, login } = require('./auth-helper');
const { baseUrl, username, password, walletName, payLinkEmail } = getConfig();

// Use the login helper for authentication
await login(page);
```

**CRITICAL RULES FOR TEST FILES:**
- **NEVER hardcode URLs, usernames, passwords, or any configuration values directly in code!**
- **NEVER use fallback values with || operators** (e.g., NEVER write `process.env.VAR || 'default'`)
- **If an environment variable is missing, throw an error** - don't provide defaults
- **ALWAYS use auth-helper.js for all test scripts - no exceptions!**
- **This applies to ALL test data**: URLs, usernames, passwords, email addresses, lightning addresses, amounts, etc.
- **NEVER create duplicate files with suffixes like "-simple", "-proper", "-v2", "-new", etc.**
- **ALWAYS update the existing file instead of creating duplicates**
- **If a script doesn't work, FIX IT - don't create a new one**

## Authentication Flow
**IMPORTANT**: When navigating to LNBits and you see the "Create account" page:
- Click on the "Login" link (usually at the bottom saying "Already have an account? Login")
- This takes you to the actual login page where you can enter credentials
- The Create account page appears even when accounts exist - always click through to Login
- This is a common issue that comes up frequently in testing

**POPUP HANDLING**: You may need to close the "I understand" popup that appears on some LNBits instances before proceeding with authentication or navigation.

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
- **API Tests**: `/tests/api/*.py` - Python-based API endpoint testing
- **UI Tests**: `/tests/ui/*.js` - Playwright browser automation testing
- **Test Runners**: Shell scripts to orchestrate all testing

#### Test Scripts
**UI Tests (Playwright):**
- **tests/ui/create_admin_account.js** - Creates initial superuser account on fresh LNBits install
- **tests/ui/login_test.js** - Tests admin login functionality
- **tests/ui/enable_allowance.js** - Enables the allowance extension via UI
- **tests/ui/create_allowance.js** - End-to-end allowance creation test
- **tests/ui/edit_allowance.js** - Tests allowance editing through forms
- **tests/ui/delete_allowance.js** - Tests allowance deletion functionality
- **tests/ui/check-currencies.js** - Tests currency dropdown functionality

**API Tests (Python):**
- **tests/api/allowance_create.py** - Tests allowance creation API
- **tests/api/allowance_read.py** - Tests allowance retrieval API
- **tests/api/allowance_update.py** - Tests allowance update API
- **tests/api/allowance_delete.py** - Tests allowance deletion API
- **tests/api/currency_rate.py** - Tests currency conversion API
- **tests/api/scheduled_payments.py** - Tests scheduled payment execution

**Test Runners:**
- **run_all_tests.sh** - Runs both API and UI tests in sequence
- **run_api_tests.sh** - Runs only API tests (Python, requires system packages)
- **run_ui_tests.sh** - Runs only UI tests (Playwright)

**Test Dependencies:**
Install Python dependencies with:
```bash
sudo apt install python3-httpx python3-pytest python3-loguru
```

**Running Tests:**
```bash
# Run all tests (API + UI)
./tests/run_all_tests.sh

# Run individual test suites
./tests/run_api_tests.sh
./tests/run_ui_tests.sh
```

#### Test Naming Conventions
- **API Tests**: Located in `tests/api/` directory with descriptive names
- **UI Tests**: Located in `tests/ui/` directory with descriptive names
- Use descriptive action-based names (create_allowance.js, not step1.js)
- Avoid "temp", "tmp", "simple", "quick" test script names - use descriptive action names instead
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
- Allowance deletion via API (DELETE requests successful)
- Chronological ordering by created_at timestamp (newest first)
- Proper error handling and exit codes
- Vue app mounting following LNURLP pattern
- Form validation with required field defaults
- Clean test suite with no false failures

### Repository Structure
The repository follows a clean structure with proper .gitignore patterns:

```
allowance/
├── tests/                    # Comprehensive test suite
│   ├── api/                 # API endpoint tests (Python)
│   │   ├── allowance_*.py   # CRUD operations testing
│   │   ├── currency_rate.py # Currency conversion testing
│   │   └── scheduled_payments.py # Scheduled payments testing
│   ├── ui/                  # UI automation tests (Playwright)
│   │   ├── create_admin_account.js
│   │   ├── login_test.js
│   │   ├── enable_allowance.js
│   │   ├── create_allowance.js
│   │   ├── edit_allowance.js
│   │   ├── delete_allowance.js
│   │   └── check-currencies.js
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

#### Local Development Testing
To ensure your code passes CI checks, run these formatting and linting tools locally:

```bash
# Install code quality tools using pipx (recommended)
pipx install black
pipx install mypy
pipx install ruff

# Or install in a virtual environment
python3 -m venv .test-venv
source .test-venv/bin/activate
pip install black mypy ruff pydantic fastapi

# Format code with Black (CI requires this)
black .

# Check formatting without modifying files
black --check .

# Run type checking with mypy
mypy --ignore-missing-imports *.py

# Run linting with ruff
ruff check .

# Clean up virtual environment if used
deactivate
rm -rf .test-venv
```

**Important**: The GitHub Actions CI workflow runs `black --check .` and will fail if code is not properly formatted. Always run `black .` before committing to avoid CI failures.

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
- **Production URL**: https://lnbits-allowance.weeksfamily.me/ (NOT localhost:5001)
- **Database Fields**: Use `start_datetime` and `end_datetime` (NOT start_date/end_date)

### Docker Volume Mounting Issues
**CRITICAL WARNING**: The current docker-compose.yml mounts the entire git repository (`.:/app/lnbits/extensions/allowance`) as the extension directory. This causes two major problems:

1. **Extension Loading Failure**: LNBits cannot properly load the extension because it sees extra files (`.git/`, `tests/`, `docker-compose.yml`, etc.) that shouldn't be in an extension directory
2. **Data Loss Risk**: Uninstalling the allowance extension via LNBits UI will DELETE the entire git repository including all development files

**Solution**: The docker-compose volume mounting needs to be changed to only mount the necessary extension files, not the entire repository directory.
- **Transaction Memos**: Use format `#allowance: {name}` for better tracking

### Configuration Management
- **NEVER hardcode credentials, URLs, or sensitive data**
- ALL configuration MUST come from environment variables via `.env.local`
- Test scripts MUST use `auth-helper.js` which loads from `.env.local`
- Required `.env.local` variables:
  ```
  TEST_LNBITS_URL=https://lnbits-allowance.weeksfamily.me
  LNBITS_ADMIN_USERNAME=ben.weeks
  LNBITS_ADMIN_PASSWORD=zUYmy&05&uZ$3kmf*^T8
  RECEIVING_WALLET_NAME=Receiving
  PAYLINK_EMAIL=receiving@lnbits-allowance.weeksfamily.me
  ```

### UI/UX Improvements
- **Decimal Amounts**: Non-sats currencies (GBP, USD, etc.) support decimal amounts (e.g., 0.01)
- **Popup Scrolling**: Forms are scrollable on small screens to access all fields and buttons
- **Optional Start Date**: If not specified, defaults to current datetime
- **Field Labels**:
  - "Start date & time (optional)"
  - "End date & time (optional)"

### Testing Best Practices
- Use "Minutely" frequency for rapid testing with 5-minute end times
- Always capture screenshots at key test points
- Verify transactions after tests using `verify_transactions.py`
- Test scripts should be descriptive: `create-paylink.js` not `step1.js`
- Chain scripts when needed (e.g., paylink creation requires wallet creation first)

### Repo Interaction Guidelines
- Do not send or create pull requests to https://github.com/lnbits/myextension (or make any changes to that repo)