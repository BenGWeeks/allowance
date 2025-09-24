# Code Review: views_api.py

## Summary
The API implementation is functional but has several critical issues around database access, code duplication, and architectural patterns.

## 🔴 Critical Issues

### 1. **Hardcoded Database Connection**
Every endpoint creates a new connection with hardcoded credentials:
```python
conn = await asyncpg.connect(
    "postgresql://lnbits:password@allowance-postgres:5432/lnbits"
)
```

**Problems:**
- Security risk (hardcoded password)
- No connection pooling (performance issue)
- Different from how LNBits extensions should work

**Fix:** Should use LNBits' `db` wrapper from crud.py

### 2. **Bypassing LNBits ORM**
The code directly uses asyncpg instead of the LNBits database abstraction layer used in crud.py.

**Problems:**
- Inconsistent with rest of extension
- Breaks if LNBits changes database backend
- Duplicates logic from crud.py

**Fix:** Use the existing crud.py functions

### 3. **Duplicate parse_datetime_string Function**
The same function is defined twice (lines 212 and 358).

**Fix:** Define once and reuse

### 4. **Manual Authentication Instead of Decorators**
Every endpoint manually checks API keys instead of using LNBits decorators.

**Problems:**
- Code duplication
- Potential security issues
- Not following LNBits patterns

**Fix:** Use `@require_admin_key` decorator properly

## ⚠️ Code Quality Issues

### 5. **Commented Dead Code**
Lines 439-442, 535-542 contain commented-out code that should be removed.

### 6. **Inconsistent Error Handling**
Some endpoints return empty lists on error (line 134), others raise exceptions.

### 7. **Manual Trigger Endpoint Duplicates Scheduler Logic**
Lines 586-691 duplicate logic from tasks.py

**Fix:** Call the existing functions from tasks.py

### 8. **Missing Data Validation**
No validation on:
- Lightning address format
- Amount limits
- Frequency type values

## ✅ Good Points

1. **Comprehensive logging** - Good use of emojis and clear messages
2. **Proper HTTP status codes** - Correct use of 401, 403, 404, etc.
3. **Ownership verification** - Checks wallet ownership before operations
4. **Timezone handling** - Attempts to handle timezones properly

## 📝 Recommended Refactoring

### Current Pattern (Bad):
```python
async def api_allowances(request: Request, ...):
    # Manual auth check
    api_key = request.headers.get("X-Api-Key")
    # ... validation ...

    # Direct DB connection
    conn = await asyncpg.connect("postgresql://...")
    rows = await conn.fetch("SELECT ...")
    await conn.close()
```

### Recommended Pattern (Good):
```python
@allowance_api_router.get("/api/v1/allowance")
async def api_allowances(
    wallet: Wallet = Depends(require_admin_key),
    all_wallets: bool = Query(False)
):
    # Use crud.py functions
    allowances = await get_allowances(wallet.id)
    return [a.dict() for a in allowances]
```

## 🎯 Priority Fixes

1. **HIGH**: Remove hardcoded database credentials
2. **HIGH**: Use LNBits database abstraction
3. **MEDIUM**: Fix duplicate code
4. **MEDIUM**: Use proper decorators
5. **LOW**: Remove dead code

## Security Concerns

1. **Hardcoded credentials** in plain text
2. **SQL injection risk** minimized by parameterized queries (good)
3. **No rate limiting** on manual trigger endpoint

## Performance Issues

1. **No connection pooling** - Creates new connection per request
2. **No caching** - Could cache currency rates
3. **Inefficient queries** - Could use JOIN instead of multiple queries

## Next Steps

1. Refactor to use crud.py functions consistently
2. Remove direct database access
3. Use LNBits decorators properly
4. Add proper input validation
5. Consider adding unit tests for API endpoints