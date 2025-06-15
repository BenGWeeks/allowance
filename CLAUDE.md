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

### Development Environment
- Make sure you are working on the dev docker of lnbits (running on port 5001), not the production version (running on port 5000)
- When looking for best practice of how to create an extension, look at https://github.com/lnbits/lnbits/tree/main/lnbits/extensions/lnurlp (do not download it, just look at the source)

## Preventing Merge Conflicts in Pull Requests

### Root Causes (Now Resolved)
1. **Runtime Files Tracked**: The `data/` directory containing logs, auth keys, and runtime files was being tracked by git, causing constant conflicts. This is now resolved with proper `.gitignore` patterns.

2. **Parallel Development**: Multiple issue branches being developed simultaneously can create conflicting changes.

### Best Practices to Minimize Future Conflicts

#### 1. Keep Branches Short-Lived and Focused
- Create branch → Make targeted changes → Create PR → Merge quickly
- Avoid long-running feature branches that diverge significantly from main
- Focus each branch on a single issue or feature

#### 2. Rebase Before Creating PRs
```bash
# Before creating a PR, update your branch with latest main:
git fetch origin main
git rebase origin/main

# If conflicts occur during rebase, resolve them incrementally:
git status                    # See conflicted files
# Edit files to resolve conflicts
git add <resolved-files>
git rebase --continue
```

#### 3. Use GitHub's "Update Branch" Feature
- When GitHub shows merge conflicts on a PR, use the "Update branch" button first
- This merges main into your branch through GitHub's interface
- Often resolves conflicts automatically without manual intervention

#### 4. Keep Main Branch Updated Locally
```bash
# Regularly update your local main branch:
git checkout main
git pull origin main

# When starting new work, ensure you're on latest main:
git checkout main
git pull origin main
git checkout -b feature/new-branch
```

#### 5. Monitor .gitignore Completeness
Ensure these patterns are properly ignored to prevent runtime file conflicts:
```gitignore
# Runtime data (Docker volumes)
data/
pgdata/
*.log

# Test artifacts
tests/test-results/
test-results/
*.png
*.json

# Temporary files
temp/
.pytest_cache/
__pycache__/

# IDE files
.vscode/
.idea/
```

#### 6. Communication and Coordination
- Review other open PRs before starting work to avoid overlapping changes
- If working on related features, coordinate with other developers
- Consider smaller, incremental PRs rather than large feature drops

#### 7. Conflict Resolution Workflow
When conflicts do occur:
1. **Don't panic** - conflicts are normal in active development
2. **Fetch latest main**: `git fetch origin main`
3. **Merge or rebase**: Choose based on preference (rebase for cleaner history)
4. **Resolve conflicts systematically**: Handle one file at a time
5. **Test after resolution**: Ensure functionality still works
6. **Commit with clear message**: Explain what was resolved

### Expected Reduction in Conflicts
With the `data/` directory now properly ignored and these practices in place, merge conflicts should be significantly reduced. Most future conflicts will be legitimate code conflicts that require human decision-making rather than spurious runtime file conflicts.

## Cleaning Up Messy PRs

### When PRs Show Too Many Files
If a PR shows many unrelated file changes (like 140+ files when you only changed 3):

1. **Identify the Problem**: Usually caused by merging main that has cleanup changes
2. **Reset and Cherry-Pick**: 
   ```bash
   # Reset to a clean state
   git reset --soft HEAD~N  # N = number of commits to undo
   
   # Or checkout files from main to reset
   git checkout origin/main -- .
   
   # Then stage only your specific changes
   git add path/to/your/specific/files
   ```

3. **Force Push Carefully**:
   ```bash
   git push --force-with-lease origin branch-name
   ```

### Avoiding Log File Conflicts
The `data/` directory often contains Docker-managed files that cause conflicts:
- **Never commit log files**: Even temporarily to resolve conflicts
- **If stuck with permission errors**: Stage other files and ignore logs
- **Check Docker usage**: `lsof filename` to see if files are in use

### Clean PR Best Practices
1. **Minimal Changes**: Only commit files directly related to your issue
2. **Review Before Push**: Use `git status` and `git diff --cached`
3. **Descriptive Commits**: Explain what changed and why
4. **Test Locally**: Ensure your changes work before pushing