# Allowance (LNbits extension)

Native Python LNbits extension that pays scheduled allowances from a funded wallet. Bugs can move real money, so treat payment, scheduling and validation changes with care.

- Reference implementation: https://github.com/lnbits/myextension (docs may be stale). For patterns, read the official `lnurlp` extension source; don't vendor it.
- Never open PRs against or change `lnbits/myextension`.
- Compatibility, CI coverage and the release process: `README.md` → "LNbits compatibility" and `docs/releasing.md`. Bump `min_lnbits_version` in `config.json` only with a matching CI matrix change.

## Secrets and configuration

- **Never commit credentials, keys, wallet IDs or real URLs.** This repo is public. Not in code, docs, examples, test fixtures or this file.
- Local values live in git-ignored files: `.env.local` (UI/API test login) and `.env.test` (wallet IDs and keys). Copy them from `.env.example` and `.env.test.example`, which must only ever contain placeholders.
- Test scripts read configuration via `tests/ui/auth-helper.js` (`getConfig()`, `login(page)`). If a variable is missing, throw. Never fall back to defaults (`process.env.X || '…'`) and never hardcode test data (URLs, users, passwords, addresses, amounts).

## Development environment

- `docker-compose.yml` runs a FakeWallet dev instance on **http://localhost:5002** (`lnbits-dev`, data in `./data-dev`). Work there, never against a production instance.
- **Warning:** the dev service mounts the whole repo as the extension directory (`.:/app/lnbits/extensions/allowance`). Uninstalling Allowance from that instance's UI deletes the checkout, `.git` included. Don't uninstall it there.
- Restart the container after `config.json` changes; the extensions page caches metadata.
- Database fields are `start_datetime` / `end_datetime` (not `start_date` / `end_date`). Payment memos use `#allowance: {name}`.

## Checks before committing

```bash
python3 tests/run_ci_checks.py   # all CI quality checks
# or individually (versions pinned in pyproject.toml):
black --check .
ruff check .
mypy .
```

CI (`.github/workflows/api-unit-tests.yml`) runs the offline unit suite inside the official LNbits images in its matrix, plus PostgreSQL, release-archive installation and quality jobs. To run the unit suite the same way:

```bash
docker run --rm --network none -e LNBITS_DATA_FOLDER=/tmp/allowance-tests \
  -e LNBITS_BACKEND_WALLET_CLASS=FakeWallet -e LOGURU_LEVEL=ERROR \
  -v "$PWD:/app/lnbits/extensions/allowance:ro" lnbits/lnbits:<version> \
  /app/.venv/bin/python /app/lnbits/extensions/allowance/tests/run_unit_tests.py
```

## Tests

- `tests/unit/`: offline unit and regression tests (the CI suite).
- `tests/api/`: Python scripts against a live instance (`create-allowance.py`, `check-scheduled-payments.py`, …).
- `tests/ui/`: Playwright. `setup/` provisions an instance (admin account, extensions, wallets, paylinks); `crud/` exercises allowances.
- Runners: `tests/run_all_tests.sh`, `run_api_tests.sh` (`--all` adds long scheduled-payment tests, which need a 10+ minute timeout), `run_ui_tests.sh`, `run_postgres_tests.sh`, `run_release_tests.sh`.
- Use the "minutely" frequency with a short end time to test schedules quickly. Verify the resulting transactions afterwards.
- Name scripts by action (`create-allowance.js`, not `step1.js` or `-v2` / `-simple` copies). Fix an existing script rather than duplicating it.
- Scripts exit 0 on success and non-zero on failure. Capture screenshots at key steps (`test-results/` is git-ignored).

### Playwright tips

- LNbits may show "Create account" even when accounts exist. Click through to "Login".
- Dismiss the "I understand" popup if it appears.
- Prefer `aria-label` selectors (`[aria-label="Username"]`). Scope by card text (`.q-card:has(.text-h5:has-text("Allowance"))`). Confirm state changes by button text (Enable → Disable).

## Frontend gotchas (Vue 3 / Quasar)

- Mount like `lnurlp`: `window.app = Vue.createApp({ el: '#vue', mixins: [window.windowMixin], … })` with **no** `.mount('#vue')` call. LNbits mounts the app, and calling `.mount()` triggers the `this.$q.localStorage` undefined error.
- `windowMixin` is required (user, wallets, Quasar helpers).
- Trigger saves with `@click` on the button, not form `@submit.prevent`.
- Give every required field a default in `openCreateDialog()` (e.g. `frequency_type`). Map every field in `openUpdateDialog()`. Missing fields fail validation silently.
