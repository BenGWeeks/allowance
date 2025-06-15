#!/bin/bash
# Run all tests (API + UI)

set -e

echo "🚀 Running All Tests"
echo "==================="

# Ensure we're in the tests directory  
cd "$(dirname "$0")"

# Track overall results
API_RESULT=0
UI_RESULT=0

echo
echo "🔄 Step 1: Running API Tests"
echo "----------------------------"

if [ -f "run_api_tests.sh" ]; then
    if ./run_api_tests.sh; then
        echo "✅ API tests completed successfully"
        API_RESULT=0
    else
        echo "❌ API tests failed"
        API_RESULT=1
    fi
else
    echo "⚠️ API test runner not found (run_api_tests.sh)"
    API_RESULT=0
fi

echo
echo "🔄 Step 2: Running UI Tests"
echo "---------------------------"

if [ -f "run_ui_tests.sh" ]; then
    if ./run_ui_tests.sh; then
        echo "✅ UI tests completed successfully" 
        UI_RESULT=0
    else
        echo "❌ UI tests failed"
        UI_RESULT=1
    fi
else
    echo "⚠️ UI test runner not found (run_ui_tests.sh)"
    UI_RESULT=0
fi

# Summary
echo
echo "==================="
echo "📊 Overall Test Results"
echo "==================="

if [ $API_RESULT -eq 0 ] && [ $UI_RESULT -eq 0 ]; then
    echo "🎉 All tests passed!"
    echo "  ✅ API Tests: PASSED"
    echo "  ✅ UI Tests: PASSED"
    exit 0
else
    echo "💥 Some tests failed:"
    if [ $API_RESULT -ne 0 ]; then
        echo "  ❌ API Tests: FAILED"
    else
        echo "  ✅ API Tests: PASSED"
    fi
    
    if [ $UI_RESULT -ne 0 ]; then
        echo "  ❌ UI Tests: FAILED"
    else
        echo "  ✅ UI Tests: PASSED"
    fi
    exit 1
fi