# Code Review: tasks.py

## Summary
The scheduler logic is mostly solid but had a critical bug causing repeated processing of expired allowances. The fixes applied should resolve the issue.

## Fixed Issues
1. ✅ **Deactivation persistence bug** - Added tracking of deactivated IDs
2. ✅ **Redundant timezone code** - Created helper function
3. ✅ **Unnecessary active check** - Removed redundant check since query already filters

## Remaining Concerns

### 1. Invoice Listener (lines 24-66)
The `wait_for_paid_invoices()` and `on_invoice_paid()` functions appear to be unused. The extension uses scheduled outgoing payments, not incoming invoice payments.

**Recommendation:** Remove if unused, or document its purpose if needed for future features.

### 2. Error Recovery
Failed payments don't retry. If a payment fails due to temporary network issues, it's skipped until the next cycle.

**Recommendation:** Add retry logic with exponential backoff.

### 3. Performance Optimization
The scheduler checks ALL allowances every 60 seconds, even those with yearly frequency.

**Recommendation:** Consider:
- Different check intervals based on frequency
- Or skip allowances not due for payment in next N hours

### 4. Database Transaction Handling
The `deactivate_allowance()` call might not be committing properly if LNBits uses transactions.

**Recommendation:** Verify LNBits' db wrapper commits automatically or add explicit commit.

### 5. Race Conditions
Multiple scheduler instances could process the same allowance if running in multiple workers.

**Recommendation:** Add database-level locking or use Redis for coordination.

## Code Quality Improvements

### Before (Redundant):
```python
if start_datetime.tzinfo is None:
    start_datetime = start_datetime.replace(tzinfo=timezone.utc)
```

### After (Clean):
```python
start_datetime = ensure_timezone_aware(start_datetime)
```

## Testing Recommendations
1. Run the new `test-scheduler-deactivation.py` to verify the fix works
2. Monitor Docker logs to ensure "has expired" messages stop repeating
3. Check database directly to confirm `active` field updates persist

## Next Steps
1. Test the fixes in production
2. Consider implementing retry logic for failed payments
3. Add metrics/monitoring for scheduler health
4. Document the invoice listener purpose or remove if unused