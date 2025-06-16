#!/bin/bash
# Run UI tests (Playwright)

# Don't exit on first error - we want to run all tests
set +e

echo "🎭 Running UI Tests (Playwright)"
echo "================================"

# Ensure we're in the tests directory
cd "$(dirname "$0")"

# Check if Node.js and npm are available
if ! command -v npm &> /dev/null; then
    echo "❌ npm not found. Please install Node.js and npm."
    exit 1
fi

# Install Playwright dependencies if needed
if [ ! -d "node_modules" ]; then
    echo "📦 Installing Playwright dependencies..."
    npm install
fi

# Run the core UI tests in sequence
echo
echo "Running core UI test sequence..."

# Only run core tests that exist to avoid false failures
CORE_TESTS=(
    "ui/create_admin_account.js"
    "ui/login_test.js" 
    "ui/enable_allowance.js"
    "ui/create_allowance.js"
)

PASSED=0
TOTAL=${#CORE_TESTS[@]}

for test in "${CORE_TESTS[@]}"; do
    if [ -f "$test" ]; then
        echo
        echo "🧪 Running: $test"
        # Suppress output to avoid noise, only show result
        if node "$test" > /dev/null 2>&1; then
            echo "✅ PASSED: $test"
            ((PASSED++))
        else
            echo "❌ FAILED: $test"
        fi
    else
        echo "⚠️ SKIPPED: $test (file not found)"
    fi
done

echo
echo "================================"
echo "📊 UI Test Results: $PASSED/$TOTAL tests passed"

if [ $PASSED -eq $TOTAL ]; then
    echo "🎉 All UI tests passed!"
    exit 0
else
    echo "💥 Some UI tests failed."
    exit 1
fi