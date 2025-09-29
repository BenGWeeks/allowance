#!/bin/bash
# Run UI CRUD tests (Playwright/Node.js)

# Don't exit on first error - we want to run all tests
set +e

echo "🎭 Running UI CRUD Tests (Playwright)"
echo "====================================="

# Ensure we're in the tests directory
cd "$(dirname "$0")"

# Check if Node.js is available
if ! command -v node &> /dev/null; then
    echo "❌ node not found. Please install Node.js."
    exit 1
fi

# Check if Playwright is installed
if [ ! -d "ui/node_modules" ]; then
    echo "⚠️ Playwright not installed. Installing dependencies..."
    cd ui && npm install && cd ..
fi

# Create test-screenshots directory if it doesn't exist
mkdir -p ui/test-screenshots

echo
echo "🧪 Running CRUD operation tests..."
echo

PASSED=0
FAILED=0

# Define CRUD tests to run
CRUD_TESTS=(
    "crud/create-allowance.js:Create Allowance"
    "crud/read-allowances.js:Read Allowances"
    "crud/update-allowance.js:Update Allowance"
    "crud/delete-allowance.js:Delete Allowance"
    "crud/delete-all-test-allowances.js:Cleanup Test Allowances"
)

# Run each test
for test_entry in "${CRUD_TESTS[@]}"; do
    IFS=':' read -r test_file test_name <<< "$test_entry"

    if [ -f "ui/$test_file" ]; then
        echo "📝 Testing: $test_name"
        echo "   Running: ui/$test_file"

        cd ui
        if timeout 60 node "$test_file" > test_output.tmp 2>&1; then
            # Check output for success indicators
            if grep -q "✅.*successfully\|passed\|PASSED" test_output.tmp; then
                echo "   ✅ PASSED: $test_name"
                ((PASSED++))
            else
                echo "   ⚠️ COMPLETED: $test_name (check output for details)"
                tail -5 test_output.tmp | sed 's/^/      /'
                ((PASSED++))
            fi
        else
            echo "   ❌ FAILED: $test_name"
            tail -5 test_output.tmp | sed 's/^/      /'
            ((FAILED++))
        fi
        rm -f test_output.tmp
        cd ..
        echo
    else
        echo "⚠️ SKIPPED: $test_name (file not found: ui/$test_file)"
        ((FAILED++))
        echo
    fi
done

TOTAL=$((PASSED + FAILED))

echo "====================================="
echo "📊 UI CRUD Test Results: $PASSED/$TOTAL tests passed"
echo

if [ $PASSED -eq $TOTAL ]; then
    echo "🎉 All UI CRUD tests passed!"
    exit 0
else
    echo "💥 Some UI CRUD tests failed."
    echo
    echo "📁 Screenshots saved in: ui/test-screenshots/"
    echo "   View them to debug any failures"
    exit 1
fi