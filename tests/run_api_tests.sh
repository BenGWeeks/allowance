#!/bin/bash
# Run API tests (Python)

set -e

echo "🐍 Running API Tests (Python)"
echo "============================="

# Ensure we're in the tests directory
cd "$(dirname "$0")"

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ python3 not found. Please install Python 3."
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d ".api_test_env" ]; then
    echo "📦 Creating virtual environment for API tests..."
    python3 -m venv .api_test_env
fi

# Activate virtual environment
source .api_test_env/bin/activate

# Install dependencies
echo "📦 Installing API test dependencies..."
pip install httpx pytest pytest-asyncio

# Find and run API test files
API_TESTS=($(find . -name "api_*.py" -type f))

if [ ${#API_TESTS[@]} -eq 0 ]; then
    echo "⚠️ No API test files found (api_*.py)"
    echo "📁 Current directory contents:"
    ls -la api_*.py 2>/dev/null || echo "  No api_*.py files found"
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

for test in "${API_TESTS[@]}"; do
    echo
    echo "🧪 Running: $test"
    if python3 "$test"; then
        echo "✅ PASSED: $test"
        ((PASSED++))
    else
        echo "❌ FAILED: $test"
    fi
done

# Deactivate virtual environment
deactivate

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