# Allowance - An [LNbits](https://github.com/lnbits/lnbits) Extension

## Introduction

This is an LNBits extension that allows you to setup recurring transfers between wallets.

### Installation

Install and enable the "Allowance" extension either through the official LNbits manifest (**not yet vetted**) or by adding https://raw.githubusercontent.com/bengweeks/allowance/main/manifest.json to `Server`/ `Server` / `Extension Sources`.

### Development

> This guide assumes you're using this extension as a base for a new one, and have installed LNbits using https://github.com/lnbits/lnbits/blob/main/docs/guide/installation.md#option-1-recommended-poetry.

To install LNbits see: https://github.com/lnbits/lnbits/blob/main/docs/guide/installation.md#option-1-recommended-poetry.

> LNBits cannot be installed on Windows.

1. `Ctrl c` shut down your LNbits installation.
2. Download the extension files from https://github.com/bengweek/allowance to a folder outside of `/lnbits`, and initialize the folder with `git`. Alternatively, create a repo, copy the allowance extension files into it, then `git clone` the extension to a location outside of `/lnbits`.
3. Remove the installed extension from `lnbits/lnbits/extensions`.
4. Create a symbolic link using `ln -s /home/ben/Projects/<name of your extension> /home/ben/Projects/lnbits/lnbits/extensions`.
5. Restart your LNbits installation. You can now modify your extension and `git push` changes to a repo.
6. When you're ready to share your manifest so others can install it, edit `/lnbits/allowance/manifest.json` to include the git credentials of your extension.
7. IMPORTANT: If you want your extension to be added to the official LNbits manifest, please follow the guidelines here: https://github.com/lnbits/lnbits-extensions#important

### Features

- **Recurring Transfers**: Set up automated transfers between wallets
- **Flexible Scheduling**: Support for various frequencies (per second, per minute, hourly, daily, weekly, monthly)
- **Currency Support**: Multi-currency support with real-time conversion hints
- **Vue.js Frontend**: Modern reactive interface following LNBits patterns
- **Comprehensive Testing**: Full Playwright test suite for automated testing

### Testing

The extension includes a comprehensive test suite using Playwright for automated browser testing.

#### Prerequisites

```bash
cd tests
npm install
```

#### Test Scripts

- **create-admin-account.js** - Creates initial superuser account on fresh LNBits install
- **login-test.js** - Tests admin login functionality  
- **enable-allowance.js** - Enables the allowance extension via UI
- **create-allowance.js** - End-to-end test that creates a new allowance
- **run_test.sh** - Runs all tests in sequence

#### Running Tests

```bash
# Run all tests
cd tests
./run_test.sh

# Run individual tests
node create-admin-account.js
node login-test.js  
node enable-allowance.js
node create-allowance.js
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

### Code Quality & CI/CD

#### Local Development Testing

Before pushing changes, run local quality checks to ensure GitHub Actions CI will pass:

```bash
# Quick test script
python3 -m venv .test-venv
source .test-venv/bin/activate
pip install black mypy ruff pydantic fastapi

# Run all linting checks
black --check *.py          # Code formatting
ruff check *.py             # Modern Python linting  
mypy --ignore-missing-imports *.py  # Type checking

# Clean up
rm -rf .test-venv
```

#### GitHub Actions Pipeline

The repository includes comprehensive automated testing:

- **Code Quality**: Black, Ruff, MyPy, Pyright
- **Dependency Management**: Poetry with proper Python version constraints
- **End-to-End Testing**: Playwright browser automation
- **Integration Testing**: Full LNBits environment with PostgreSQL

#### Configuration Files

- `pyproject.toml` - Python dependencies and tool configuration
- `.github/workflows/` - CI/CD pipeline definitions
- `.gitignore` - Excludes data/, temp/, and test results

### Repository Structure

```
allowance/
├── .github/workflows/       # CI/CD pipeline configuration
├── tests/                   # Playwright E2E test scripts
│   ├── create-admin-account.js
│   ├── login-test.js
│   ├── enable-allowance.js
│   ├── create-allowance.js
│   └── run_test.sh
├── static/js/              # Vue.js frontend
├── templates/allowance/    # HTML templates
├── crud.py                 # Database operations
├── views.py                # Frontend routes
├── views_api.py           # API endpoints
├── models.py              # Pydantic data models
├── tasks.py               # Background task processing
├── migrations.py          # Database schema
├── pyproject.toml         # Python dependencies & tool config
└── manifest.json          # Extension manifest
```

### Recent Improvements

- ✅ Fixed API authentication issues (403 Forbidden errors)
- ✅ Resolved Vue.js mounting and form submission problems
- ✅ Added comprehensive currency support with conversion hints
- ✅ Implemented proper form validation with required field defaults
- ✅ Clean repository structure with proper .gitignore patterns
- ✅ Full test coverage with descriptive naming conventions
