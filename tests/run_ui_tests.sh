#!/bin/bash
# Run UI tests (Playwright)

set -e

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

TESTS=(
    "ui/create_admin_account.js"
    "ui/login_test.js" 
    "ui/enable_allowance.js"
    "ui/create_allowance.js"
    "ui/edit_allowance.js"
    "ui/delete_allowance.js"
    "ui/check-currencies.js"
)

PASSED=0
TOTAL=${#TESTS[@]}

for test in "${TESTS[@]}"; do
    if [ -f "$test" ]; then
        echo
        echo "🧪 Running: $test"
        if node "$test"; then
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