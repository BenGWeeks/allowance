#!/bin/bash
# Run API tests (Python)

# Don't exit on first error - we want to run all tests
set +e

echo "🐍 Running API Tests (Python)"
echo "============================="

# Ensure we're in the tests directory
cd "$(dirname "$0")"

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ python3 not found. Please install Python 3."
    exit 1
fi

# Check if dependencies are available
echo "🔍 Checking if dependencies are available..."
if python3 -c "import httpx, pytest, loguru" 2>/dev/null; then
    echo "✅ Dependencies available"
else
    echo "❌ Missing dependencies. Please install with:"
    echo "   sudo apt install python3-httpx python3-pytest python3-loguru"
    echo "   or: pip3 install --break-system-packages httpx pytest pytest-asyncio loguru"
    exit 1
fi

# Find and run API test files
API_TESTS=($(find ./api -name "*.py" -type f))

if [ ${#API_TESTS[@]} -eq 0 ]; then
    echo "⚠️ No API test files found in ./api/"
    echo "📁 Current directory contents:"
    ls -la ./api/*.py 2>/dev/null || echo "  No API test files found"
    exit 0
fi

echo
echo "Found ${#API_TESTS[@]} API test file(s):"
for test in "${API_TESTS[@]}"; do
    echo "  📄 $test"
done

PASSED=0
TOTAL=${#API_TESTS[@]}

echo
echo "Running API tests..."

# Run all core tests (quick tests only by default)
CORE_TESTS=(
    "./api/create-allowance.py"
    "./api/read-allowance.py"
    "./api/update-allowance.py"
    "./api/delete-allowance.py"
    "./api/create-currency-allowance.py"
    "./api/check-currency-rate.py"
    "./api/create-active-minutely.py"
    "./api/update-expired-allowances.py"
)

# Long-running tests (skipped by default, run with --all flag)
LONG_TESTS=(
    "./api/check-scheduled-payments.py"
    "./api/check-minutely-allowances.py"
)

for test in "${CORE_TESTS[@]}"; do
    if [ -f "$test" ]; then
        echo
        echo "🧪 Running: $test"
        # Suppress warnings to avoid false failure appearance
        if python3 "$test" 2>/dev/null; then
            echo "✅ PASSED: $test"
            ((PASSED++))
        else
            echo "❌ FAILED: $test"
        fi
    else
        echo "⚠️ SKIPPED: $test (file not found)"
    fi
done

TOTAL=${#CORE_TESTS[@]}

# Check for flags
RUN_ALL=false
SKIP_CLEANUP=false

for arg in "$@"; do
    case $arg in
        --all)
            RUN_ALL=true
            ;;
        --no-cleanup)
            SKIP_CLEANUP=true
            ;;
    esac
done

# Run long-running tests if --all flag was passed
if [ "$RUN_ALL" = true ]; then
    echo
    echo "Running long-running tests..."
    for test in "${LONG_TESTS[@]}"; do
        if [ -f "$test" ]; then
            echo
            echo "🧪 Running (long): $test"
            echo "⏱️  This test may take 2-3 minutes..."
            if timeout 180 python3 "$test" 2>/dev/null; then
                echo "✅ PASSED: $test"
                ((PASSED++))
            else
                echo "❌ FAILED or TIMEOUT: $test"
            fi
            ((TOTAL++))
        fi
    done
else
    echo
    echo "ℹ️  Skipped long-running tests. Use '--all' flag to run them:"
    for test in "${LONG_TESTS[@]}"; do
        echo "   - $test"
    done
fi

echo
echo "============================="
echo "📊 API Test Results: $PASSED/$TOTAL tests passed"

# Run cleanup unless --no-cleanup flag was passed
if [ "$SKIP_CLEANUP" = true ]; then
    echo
    echo "ℹ️  Skipping cleanup (--no-cleanup flag passed)"
    echo "   Test allowances remain in the database"
else
    echo
    echo "🧹 Running cleanup..."
    if python3 "./api/delete-all-test-allowances.py" 2>/dev/null; then
        echo "✅ Cleanup completed"
    else
        echo "⚠️ Cleanup may have failed"
    fi
fi

if [ $PASSED -eq $TOTAL ]; then
    echo "🎉 All API tests passed!"
    exit 0
else
    echo "💥 Some API tests failed."
    exit 1
fi