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

### Testing

Comprehensive test suite with API unit tests, integration tests, and UI automation.

#### Prerequisites

```bash
cd tests
npm install  # For UI tests (Playwright)
python -m venv test_env
source test_env/bin/activate  # Linux/Mac
pip install fastapi uvicorn pytest  # For API tests
```

#### Running Tests

```bash
cd tests

# Run complete test suite (API + UI)
./run_all_tests.sh

# Run specific test suites
./run_api_tests.sh    # Python API unit tests + integration tests
./run_ui_tests.sh     # Playwright browser automation tests
```

#### Test Organization

**API Tests (Python/pytest):**
- `api_create_allowance.py` - Unit tests for allowance creation
- `api_list_allowances.py` - Unit tests for allowance listing
- `api_get_allowance.py` - Unit tests for single allowance retrieval
- `api_update_allowance.py` - Unit tests for allowance updates
- `api_delete_allowance.py` - Unit tests for allowance deletion
- `standalone_api_test.py` - Integration tests against live server
- `lnbits_mocks.py` - Mock framework for LNBits dependencies
- `conftest.py` - pytest configuration and fixtures

**UI Tests (JavaScript/Playwright):**
- `ui_create_admin_account.js` - Setup admin account for testing
- `ui_enable_allowance.js` - Enable the allowance extension
- `ui_create_allowance.js` - Create allowances via browser UI
- `ui_edit_allowance.js` - Edit existing allowances
- `ui_delete_allowance.js` - Delete allowances via UI
- `ui_check_currencies.js` - Currency functionality verification

#### Test Features

**API Tests:**
- Complete CRUD operation coverage
- Mocked LNBits dependencies for isolated unit testing
- Integration tests for connectivity, authentication, and security
- Proper error handling and edge case testing

**UI Tests:**
- End-to-end browser automation with standardized login
- Full allowance lifecycle testing (create, edit, delete)
- Form validation and currency selection testing
- Screenshot capture for debugging test failures

#### Test Environment

- **Development Server**: `http://localhost:5001` (LNBits dev docker)
- **Screenshots**: Saved to `test-results/` (gitignored)
- **Exit Codes**: Proper exit codes for CI/CD integration
- **Credentials**: Standardized test credentials across all UI tests
