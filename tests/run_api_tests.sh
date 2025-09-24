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

# Run all core tests
CORE_TESTS=(
    "./api/create-allowance.py"
    "./api/read-allowance.py"
    "./api/update-allowance.py"
    "./api/delete-allowance.py"
    "./api/create-currency-allowance.py"
    "./api/check-currency-rate.py"
    "./api/check-scheduled-payments.py"
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

echo
echo "============================="
echo "📊 API Test Results: $PASSED/$TOTAL tests passed"

if [ $PASSED -eq $TOTAL ]; then
    echo "🎉 All API tests passed!"
    exit 0
else
    echo "💥 Some API tests failed."
    exit 1
fi