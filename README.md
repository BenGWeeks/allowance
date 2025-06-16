# Allowance - An [LNbits](https://github.com/lnbits/lnbits) Extension

## Introduction

This is an LNBits extension that allows you to setup recurring payments from your LNBits wallet to any Lightning address (user@domain.com) or LNURL-pay endpoint. This enables scheduled payments to external services and Lightning addresses, not just wallet-to-wallet transfers within the same LNBits instance.

✅ CI/CD Status: Tests configured and working

### Installation

Install and enable the "Allowance" extension either through the official LNbits manifest (**not yet vetted**) or by adding https://raw.githubusercontent.com/bengweeks/allowance/main/manifest.json to `Server`/ `Server` / `Extension Sources`.

### Development

For development, we use Docker Compose to run LNBits:

1. Clone this repository outside of your LNBits installation
2. Create a symbolic link to your development directory:
   ```bash
   ln -s /path/to/your/allowance /path/to/lnbits/lnbits/extensions/allowance
   ```
3. Start LNBits using Docker Compose
4. Access the development instance at `http://localhost:5001`
5. Enable the Allowance extension through the Extensions menu

> Note: LNBits cannot be installed on Windows.

When ready to share your extension:
- Update `manifest.json` with your repository details
- Follow [LNBits extension guidelines](https://github.com/lnbits/lnbits-extensions#important) for official submission

### Features

- **Lightning Address Support**: Send recurring payments to any Lightning address (user@domain.com) or LNURL-pay endpoint
- **Scheduled Payments**: Automated payment execution with 1-minute minimum frequency using background tasks
- **Flexible Scheduling**: Support for various frequencies (minutely, hourly, daily, weekly, monthly, yearly)
- **Payment Tracking**: All payments are tagged as "allowance" payments in the LNBits payment history
- **Currency Support**: Multi-currency support with real-time conversion hints
- **Vue.js Frontend**: Modern reactive interface following LNBits patterns
- **Comprehensive Testing**: Full Playwright test suite for automated testing

### Testing

The extension includes comprehensive test suites for both API and UI testing.

#### Test Organization

- **API Tests**: `/tests/api/*.py` - Python-based API endpoint testing
- **UI Tests**: `/tests/ui/*.js` - Playwright browser automation testing  
- **Test Runners**: Shell scripts to orchestrate all testing

#### Prerequisites

**System Dependencies (no virtual environment needed):**
```bash
# Install Python test dependencies
sudo apt install -y python3-httpx python3-pytest python3-loguru

# Install Node.js and npm if not already installed
sudo apt install -y nodejs npm

# Install UI test dependencies
cd tests
npm install
cd ..
```

#### Test Scripts

**API Tests (Python):**
- **tests/api/allowance_create.py** - Test POST /api/v1/allowance endpoint
- **tests/api/allowance_read.py** - Test GET /api/v1/allowance endpoints  
- **tests/api/allowance_update.py** - Test PUT /api/v1/allowance/{id} endpoint
- **tests/api/allowance_delete.py** - Test DELETE /api/v1/allowance/{id} endpoint
- **tests/api/currency_rate.py** - Test GET /api/v1/rate/{currency} endpoint
- **tests/api/scheduled_payments.py** - Test scheduled payment execution

**UI Tests (Playwright):**
- **tests/ui/create_admin_account.js** - Creates initial superuser account
- **tests/ui/login_test.js** - Tests admin login functionality
- **tests/ui/enable_allowance.js** - Enables the allowance extension via UI
- **tests/ui/create_allowance.js** - End-to-end allowance creation test
- **tests/ui/edit_allowance.js** - Tests allowance editing through forms
- **tests/ui/delete_allowance.js** - Tests allowance deletion functionality
- **tests/ui/check-currencies.js** - Tests currency dropdown functionality

**Test Runners:**
- **tests/run_all_tests.sh** - Runs both API and UI tests in sequence
- **tests/run_api_tests.sh** - Runs only API tests (uses system Python packages)
- **tests/run_ui_tests.sh** - Runs only UI tests (Playwright browser automation)

#### Running Tests

```bash
# Run all tests (API + UI)
./tests/run_all_tests.sh

# Run only API tests
./tests/run_api_tests.sh

# Run only UI tests  
./tests/run_ui_tests.sh

# Run individual API tests
python3 tests/api/allowance_create.py
python3 tests/api/currency_rate.py

# Run individual UI tests
node tests/ui/create_allowance.js
```

#### Test Results

- All tests use proper exit codes (0 for success, 1 for failure)
- Screenshots are saved to `tests/test-results/` (excluded from Git)
- Tests are designed for CI/CD integration

#### Test Environment

Tests assume:
- LNBits running on `http://localhost:5001` (development environment)
- Admin credentials: `ben.weeks` / `zUYmy&05&uZ$3kmf*^T8`
- Fresh database for superuser creation test

### Testing & Quality

#### Code Formatting & Linting

To ensure your code passes CI checks, run these tools locally before committing:

```bash
# Install formatting tools (using pipx is recommended)
pipx install black
pipx install mypy  
pipx install ruff

# Format all Python files (REQUIRED for CI)
black .

# Check formatting without modifying
black --check .

# Run type checking
mypy --ignore-missing-imports *.py

# Run linting
ruff check .
```

**Important**: CI will fail if code is not formatted with Black. Always run `black .` before pushing changes.

#### GitHub Actions Testing

- **End-to-End Testing**: Full LNBits environment with PostgreSQL
- **Browser Automation**: Playwright testing of actual user workflows  
- **Extension Integration**: Real extension installation and testing

#### LNBits Extension Philosophy

*"Only submit fully working extensions. Do not add dependencies. The easier an extension is to review, the quicker the review process."* - [LNBits Guidelines](https://github.com/lnbits/lnbits-extensions)

#### Configuration Files

- `pyproject.toml` - Minimal Python dependencies
- `.github/workflows/test.yml` - Functional testing pipeline
- `.gitignore` - Excludes data/, temp/, and test results

### Repository Structure

```
allowance/
├── .github/workflows/       # CI/CD pipeline configuration
│   └── integration-tests.yml # GitHub Actions workflow
├── tests/                   # Comprehensive test suite
│   ├── api/                # API endpoint tests (Python)
│   │   ├── allowance_create.py
│   │   ├── allowance_read.py
│   │   ├── allowance_update.py
│   │   ├── allowance_delete.py
│   │   ├── currency_rate.py
│   │   └── scheduled_payments.py
│   ├── ui/                 # UI automation tests (Playwright)
│   │   ├── create_admin_account.js
│   │   ├── login_test.js
│   │   ├── enable_allowance.js
│   │   ├── create_allowance.js
│   │   ├── edit_allowance.js
│   │   ├── delete_allowance.js
│   │   └── check-currencies.js
│   ├── run_all_tests.sh    # Run all tests
│   ├── run_api_tests.sh    # Run API tests only
│   ├── run_ui_tests.sh     # Run UI tests only
│   ├── get_api_key.py      # Helper to get admin API key
│   ├── package.json        # Node.js dependencies
│   └── test_scheduled_payments.py # Additional payment tests
├── static/
│   ├── js/                 # Frontend JavaScript
│   │   └── index.js        # Vue.js application
│   └── css/                # Styles (if any)
├── templates/allowance/    # HTML templates
│   └── index.html         # Main extension page
├── __init__.py            # Extension initialization
├── config.json            # Extension configuration
├── crud.py                # Database operations
├── models.py              # Pydantic data models
├── tasks.py               # Background task processing
├── views.py               # Frontend routes
├── views_api.py           # API endpoints
├── migrations.py          # Database schema
├── manifest.json          # Extension manifest
├── pyproject.toml         # Python dependencies
├── README.md              # This file
├── CLAUDE.md              # Development notes
└── .gitignore             # Git ignore patterns
```

