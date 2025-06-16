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

# Try to run without virtual environment first
echo "🔍 Checking if dependencies are available..."
if python3 -c "import httpx, pytest" 2>/dev/null; then
    echo "✅ Dependencies available system-wide"
    USE_VENV=false
else
    echo "📦 Dependencies not available, creating virtual environment..."
    USE_VENV=true
    
    # Create virtual environment if it doesn't exist
    if [ ! -d ".api_test_env" ]; then
        python3 -m venv .api_test_env
    fi

    # Activate virtual environment
    source .api_test_env/bin/activate

    # Install dependencies
    echo "📦 Installing API test dependencies..."
    pip install httpx pytest pytest-asyncio
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

# Deactivate virtual environment if we used one
if [ "$USE_VENV" = true ]; then
    deactivate
fi

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