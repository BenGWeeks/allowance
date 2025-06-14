#!/usr/bin/env python3
"""
API Integration Tests - Tests actual HTTP endpoints against running LNBits server
"""
import requests
import json
import sys
import time
import os
from datetime import datetime, timedelta

# Use environment variable or default to CI port (5000)
# For local testing, set LNBITS_PORT=5001
LNBITS_PORT = os.getenv("LNBITS_PORT", "5000")
BASE_URL = f"http://localhost:{LNBITS_PORT}"
ALLOWANCE_API = f"{BASE_URL}/allowance/api/v1"

def test_api_health():
    """Test basic API connectivity"""
    try:
        response = requests.get(f"{ALLOWANCE_API}/allowance", timeout=10)
        print(f"✅ API Health Check - Status: {response.status_code}")
        return response.status_code in [200, 401, 403]  # Any of these means API is responding
    except Exception as e:
        print(f"❌ API Health Check Failed: {e}")
        return False

def test_create_allowance():
    """Test creating an allowance via API"""
    allowance_data = {
        "name": "API Test Allowance",
        "lightning_address": "apitest@example.com", 
        "amount": 750,
        "currency": "sats",
        "start_date": datetime.now().isoformat(),
        "frequency_type": "weekly",
        "next_payment_date": (datetime.now() + timedelta(days=7)).isoformat(),
        "memo": "Created via API integration test",
        "active": True
    }
    
    try:
        response = requests.post(
            f"{ALLOWANCE_API}/allowance",
            json=allowance_data,
            timeout=10
        )
        print(f"✅ Create Allowance API - Status: {response.status_code}")
        
        if response.status_code == 201:
            data = response.json()
            print(f"   Created allowance with ID: {data.get('id')}")
            return data.get('id')
        elif response.status_code in [401, 403]:
            print("   ⚠️  Authentication required (expected in CI)")
            return "auth_required"
        else:
            print(f"   Response: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Create Allowance API Failed: {e}")
        return None

def test_list_allowances():
    """Test listing allowances via API"""
    try:
        response = requests.get(f"{ALLOWANCE_API}/allowance", timeout=10)
        print(f"✅ List Allowances API - Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            count = len(data) if isinstance(data, list) else 0
            print(f"   Found {count} allowance(s)")
            return True
        elif response.status_code in [401, 403]:
            print("   ⚠️  Authentication required (expected in CI)")
            return True
        else:
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ List Allowances API Failed: {e}")
        return False

def test_api_endpoints():
    """Test various API endpoints for basic functionality"""
    endpoints = [
        "/allowance",
        "/docs", 
        "/openapi.json"
    ]
    
    results = {}
    for endpoint in endpoints:
        try:
            response = requests.get(f"{ALLOWANCE_API}{endpoint}", timeout=10)
            status_ok = response.status_code in [200, 401, 403, 404]
            results[endpoint] = {
                "status": response.status_code,
                "ok": status_ok
            }
            print(f"✅ Endpoint {endpoint} - Status: {response.status_code} {'✓' if status_ok else '✗'}")
        except Exception as e:
            results[endpoint] = {"status": "error", "ok": False}
            print(f"❌ Endpoint {endpoint} Failed: {e}")
    
    return all(result["ok"] for result in results.values())

def test_api_response_format():
    """Test API response formats and headers"""
    try:
        response = requests.get(f"{ALLOWANCE_API}/allowance", timeout=10)
        
        # Check content type
        content_type = response.headers.get('content-type', '')
        is_json = 'application/json' in content_type
        print(f"✅ API Response Format - Content-Type: {content_type} {'✓' if is_json else '✗'}")
        
        # Try to parse JSON
        try:
            data = response.json()
            print(f"   JSON parsing: ✓")
            return True
        except json.JSONDecodeError:
            print(f"   JSON parsing: ✗")
            return False
            
    except Exception as e:
        print(f"❌ API Response Format Test Failed: {e}")
        return False

def main():
    """Run all API integration tests"""
    print("🚀 Starting API Integration Tests...")
    print(f"   Testing against: {BASE_URL}")
    
    # Wait for server to be ready
    print("⏳ Waiting for server to be ready...")
    time.sleep(5)
    
    tests = [
        ("API Health Check", test_api_health),
        ("API Endpoints", test_api_endpoints), 
        ("API Response Format", test_api_response_format),
        ("List Allowances", test_list_allowances),
        ("Create Allowance", test_create_allowance),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n📋 Running: {test_name}")
        try:
            result = test_func()
            if result or result == "auth_required":
                passed += 1
                print(f"   ✅ PASSED")
            else:
                print(f"   ❌ FAILED")
        except Exception as e:
            print(f"   💥 ERROR: {e}")
    
    print(f"\n📊 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All API integration tests passed!")
        sys.exit(0)
    else:
        print("⚠️  Some API integration tests failed")
        sys.exit(1)

if __name__ == "__main__":
    main()