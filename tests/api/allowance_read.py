"""
API test for GET /api/v1/allowance - List allowances endpoint
"""

import httpx
import asyncio


async def test_list_allowances():
    """Test retrieving list of allowances via API"""
    base_url = "http://localhost:5001"

    try:
        async with httpx.AsyncClient() as client:
            # For development testing, we need an actual API key
            # This is the admin key for wallet b2a9a06ff45e439d8c00bc6406d48191
            admin_key = "d16c6bf31be03c2cd0cfadc7d90a2d69"  # Known dev admin key
            
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
        async with httpx.AsyncClient() as client:
            admin_key = "d16c6bf31be03c2cd0cfadc7d90a2d69"  # Known dev admin key

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
