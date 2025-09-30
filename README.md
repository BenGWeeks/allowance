# Allowance - An [LNbits](https://github.com/lnbits/lnbits) Extension

![Allowance Extension Banner](static/image/banner_cropped.png)

> **Note**: This extension was developed as a test of using Claude Code to build an LNBits extension, demonstrating AI-assisted development of Bitcoin Lightning applications.

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
- **Payment Tracking**: All payments are tagged as "#allowance" with the allowance name in the memo field in the LNBits payment history
- **Multi-Currency Support**: Pay in fiat currencies (USD, EUR, GBP, etc.) with automatic conversion to sats at payment time
- **Decimal Amount Support**: Precise amounts like 0.02 GBP or 0.30 USD supported
- **Vue.js Frontend**: Modern reactive interface following LNBits patterns
- **Comprehensive Testing**: Full Playwright test suite for automated testing
- **API Architecture**: Uses LNBits decorators and database abstraction (no hardcoded credentials)
- **Smart Scheduler**: Automatic deactivation of expired allowances with proper timezone handling

### Testing

The extension includes comprehensive test suites for both API and UI testing. For detailed testing procedures, see **[Testing Guide](docs/testing.adoc)**.

**Quick start:**
```bash
# Run all tests
./tests/run_all_tests.sh

# Run API tests only
./tests/run_api_tests.sh

# Run UI tests only
./tests/run_ui_crud_tests.sh
```

**Note**: Create `.env.local` with test credentials before running tests. See [Testing Guide](docs/testing.adoc) for complete setup instructions.

### Documentation

Comprehensive documentation is available in the `docs/` directory:

- **[Installation Guide](docs/installation.adoc)** - Step-by-step installation instructions
- **[FAQs](docs/faqs.adoc)** - Frequently asked questions and answers
- **[Testing Guide](docs/testing.adoc)** - Detailed testing procedures
- **[Troubleshooting Guide](docs/troubleshooting.adoc)** - Common issues and solutions

### Code Quality

Before committing, run code formatting and linting:

```bash
# Format Python files (REQUIRED for CI)
black .

# Run type checking
mypy --ignore-missing-imports *.py

# Run linting
ruff check .
```

**Important**: CI will fail if code is not formatted with Black.

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

