# Contributing to Allowance

Thanks for helping. Allowance pays real money from funded LNbits wallets on a schedule, so changes to payments, scheduling and validation need tests and careful review.

## Secrets: zero tolerance

**Leaking a secret is not acceptable, and a pull request that contains one will not be merged.** This repository is public. Anything pushed to it, in any commit, branch, pull request, issue, comment, CI log or screenshot, must be treated as published permanently. Deleting it afterwards does not undo the leak: git history, forks, clones and caches keep it.

### What counts as a secret

Passwords; LNbits admin and invoice keys; user IDs used to log in; wallet IDs; NWC connection strings; LND macaroons; Nostr private keys (`nsec…`) and other private keys; API tokens; `.lnbits_auth_key` and similar key files; and real instance URLs, usernames or email addresses from your own setup.

### Rules

1. Put real values only in the git-ignored `.env.local` and `.env.test`. Start from `.env.example` and `.env.test.example`, and keep those files **placeholder-only** (`your_username`, `your-wallet-key-here`).
2. Never hardcode credentials or real configuration in code, tests, docs, examples or agent instruction files (`AGENTS.md`, `CLAUDE.md`). Test scripts read configuration through `tests/ui/auth-helper.js` and fail if a value is missing.
3. Review `git diff --cached` before every commit. Don't commit with `git add -A` or `git commit -a` without reading what is staged.
4. Never paste secrets into pull request descriptions, issues, review comments, logs or screenshots. Redact them before sharing output.
5. GitHub secret scanning and push protection are enabled, and CI runs gitleaks on every push and pull request. Push protection only recognises provider token formats, so it will not stop a plain password: review your own diff. If either blocks something, remove the secret. Never use "allow secret" to bypass it.
6. AI coding agents follow the same rules. Their instructions are in `AGENTS.md`.

### If a secret leaks

1. **Tell the maintainer immediately, privately**, through GitHub's private vulnerability reporting (Security tab → "Report a vulnerability"). Don't open a public issue about it.
2. **Rotate or revoke the secret first.** Change the password or key, re-issue the macaroon, re-pair the NWC connection. Assume it has already been copied.
3. Then remove it from the files in a pull request. Rewriting git history is the maintainer's decision and is never a substitute for rotation.
4. Check where else it was used and rotate it there too.

## Development

See `AGENTS.md` for the dev environment, test layout and Vue/Quasar gotchas, `README.md` for LNbits compatibility, and `docs/releasing.md` for releases.

Before opening a pull request:

```bash
python3 tests/run_ci_checks.py   # black, ruff, mypy
```

CI runs the offline unit suite in the official LNbits images, PostgreSQL, release-installation, quality (black, ruff, release-builder test, JSON validation) and gitleaks checks. All must pass. Add or update tests for any change to payments, scheduling or validation.
