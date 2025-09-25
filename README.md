# Allowance - An [LNbits](https://github.com/lnbits/lnbits) Extension

## Introduction

This is an LNBits extension that allows you to setup recurring payments from your LNBits wallet to any Lightning address (user@domain.com) or LNURL-pay endpoint. Perfect for allowances, pocket money, subscriptions, and regular transfers. This enables scheduled payments to external services and Lightning addresses, not just wallet-to-wallet transfers within the same LNBits instance.

✅ CI/CD Status: Tests configured and working
✅ API Architecture: Refactored to use LNBits best practices

### Installation

Install and enable the "Allowance" extension either through the official LNbits manifest (**not yet vetted**) or by adding https://raw.githubusercontent.com/BenGWeeks/allowance/main/manifest.json to `Server`/ `Server` / `Extension Sources`.

### Development

For development, we use Docker Compose to run LNBits:

1. Clone this repository
2. Start LNBits using Docker Compose:
   ```bash
   docker-compose up -d
   ```
3. Access the development instance at `http://localhost:5001`
4. Enable the Allowance extension through the Extensions menu

The Docker Compose configuration automatically mounts the current directory into the container, so changes to the code are reflected immediately.

> Note: LNBits cannot be installed on Windows.

When ready to share your extension:
- Update `manifest.json` with your repository details
- Follow [LNBits extension guidelines](https://github.com/lnbits/lnbits-extensions#important) for official submission

### Features

- **Lightning Address Support**: Send recurring payments to any Lightning address (user@domain.com) or LNURL-pay endpoint
- **Scheduled Payments**: Automated payment execution with 1-minute minimum frequency using background tasks
- **Flexible Scheduling**: Support for various frequencies (minutely, hourly, daily, weekly, monthly, yearly)
- **Payment Tracking**: All payments are tagged as "#allowance: {name}" in the LNBits payment history
- **Multi-Currency Support**: Pay in fiat currencies (USD, EUR, GBP, etc.) with automatic conversion to sats at payment time
- **Decimal Amount Support**: Precise amounts like 0.02 GBP or 0.30 USD supported
- **Vue.js Frontend**: Modern reactive interface following LNBits patterns
- **Comprehensive Testing**: Full Playwright test suite for automated testing
- **API Architecture**: Uses LNBits decorators and database abstraction (no hardcoded credentials)
- **Smart Scheduler**: Automatic deactivation of expired allowances with proper timezone handling

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
- **tests/api/create-test-allowances.py** - Create 10 test allowances with various configurations

**UI Tests (Playwright):**
- **tests/ui/enable-allowance.js** - Enables the allowance extension via UI
- **tests/ui/create-allowance.js** - End-to-end allowance creation test
- **tests/ui/edit-allowance.js** - Tests allowance editing and metadata display
- **tests/ui/delete-allowance.js** - Tests allowance deletion functionality
- **tests/ui/check-currencies.js** - Tests currency dropdown functionality
- **tests/ui/test-date-persistence.js** - Verifies date changes persist correctly

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

#### Test Environment Configuration

**IMPORTANT**: The `.env.local` configuration is **only needed for running tests** - not for normal extension usage. Before running tests, create a `.env.local` file in the project root with your test environment configuration:

```bash
# Copy the example file and customize it
cp .env.example .env.local
```

Edit `.env.local` with your specific values:

```
TEST_LNBITS_URL=http://localhost:5001
LNBITS_ADMIN_USERNAME=your-admin-username
LNBITS_ADMIN_PASSWORD=your-admin-password
RECEIVING_WALLET_NAME=Receiving
PAYLINK_EMAIL=receiving@yourdomain.com
```

**Security Notes:**
- `.env.local` is gitignored and will never be committed
- Never hardcode credentials in test files
- All tests use the centralized auth-helper.js module
- Production deployments should use environment variables or secure credential management

**Test Requirements:**
- LNBits instance running and accessible
- Valid admin credentials for authentication
- Fresh database for initial setup tests

### Documentation

Comprehensive documentation is available in the `docs/` directory:

- **[Installation Guide](docs/installation.adoc)** - Step-by-step installation instructions
- **[FAQs](docs/faqs.adoc)** - Frequently asked questions and answers
- **[Testing Guide](docs/testing.adoc)** - Detailed testing procedures
- **[Troubleshooting Guide](docs/troubleshooting.adoc)** - Common issues and solutions

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
├── docs/                    # Documentation (AsciiDoc format)
│   ├── installation.adoc   # Installation guide
│   ├── faqs.adoc           # Frequently asked questions
│   ├── testing.adoc        # Testing procedures
│   └── troubleshooting.adoc # Problem resolution
├── tests/                   # Comprehensive test suite
│   ├── api/                # API endpoint tests (Python)
│   │   ├── allowance_*.py  # CRUD operation tests
│   │   ├── currency_rate.py # Currency conversion tests
│   │   ├── scheduled_payments.py # Payment scheduler tests
│   │   └── create-test-allowances.py # Bulk test data creation
│   ├── ui/                 # UI automation tests (Playwright)
│   │   ├── auth-helper.js  # Centralized authentication
│   │   ├── enable-allowance.js
│   │   ├── create-allowance.js
│   │   ├── edit-allowance.js
│   │   ├── delete-allowance.js
│   │   ├── check-currencies.js
│   │   └── test-date-persistence.js
│   ├── run_all_tests.sh    # Run all tests
│   ├── run_api_tests.sh    # Run API tests only
│   └── run_ui_tests.sh     # Run UI tests only
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

