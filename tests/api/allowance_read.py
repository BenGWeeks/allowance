"""
API test for GET /api/v1/allowance - List allowances endpoint
"""

import httpx
import asyncio


async def test_list_allowances():
    """Test retrieving list of allowances via API"""
    base_url = "http://localhost:5001"

    try:
        # Get admin API key dynamically
        import sys
        import os
        sys.path.append(os.path.dirname(os.path.dirname(__file__)))
        from get_api_key import get_admin_api_key
        
        admin_key = await get_admin_api_key()
        if not admin_key:
            print("❌ Failed to get admin API key")
            return False

        async with httpx.AsyncClient() as client:
            
            response = await client.get(
                f"{base_url}/allowance/api/v1/allowance",
                headers={"X-Api-Key": admin_key}
            )

            print(f"List allowances API response: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                print(f"✅ Retrieved {len(data)} allowances")
                return True
            else:
                print(f"❌ Failed to list allowances: {response.text}")
                return False

    except Exception as e:
        print(f"❌ API test error: {e}")
        return False


async def test_get_single_allowance():
    """Test retrieving a single allowance by ID via API"""
    base_url = "http://localhost:5001"
    test_id = "test_allowance_id"

    try:
        # Get admin API key dynamically
        import sys
        import os
        sys.path.append(os.path.dirname(os.path.dirname(__file__)))
        from get_api_key import get_admin_api_key
        
        admin_key = await get_admin_api_key()
        if not admin_key:
            print("❌ Failed to get admin API key")
            return False

        async with httpx.AsyncClient() as client:

            response = await client.get(
                f"{base_url}/allowance/api/v1/allowance/{test_id}",
                headers={"X-Api-Key": admin_key}
            )

            print(f"Get single allowance API response: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                print(f"✅ Retrieved allowance: {data.get('name', 'Unknown')}")
                return True
            elif response.status_code == 404:
                print(f"⚠️ Allowance not found (expected for test ID)")
                return True
            else:
                print(f"❌ Failed to get allowance: {response.text}")
                return False

    except Exception as e:
        print(f"❌ API test error: {e}")
        return False


if __name__ == "__main__":
    print("🧪 Testing allowance read endpoints...")

    success1 = asyncio.run(test_list_allowances())
    success2 = asyncio.run(test_get_single_allowance())

    if success1 and success2:
        print("✅ All read tests passed")
        exit(0)
    else:
        print("❌ Some read tests failed")
        exit(1)
