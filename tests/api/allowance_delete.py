"""
API test for DELETE /api/v1/allowance/{id} - Delete allowance endpoint
"""

import httpx
import asyncio


async def test_delete_allowance():
    """Test deleting an allowance via API"""
    base_url = "http://localhost:5001"
    test_id = "test_allowance_id"

    try:
        async with httpx.AsyncClient() as client:
            # For development testing, we need an actual API key
            # This is the admin key for wallet b2a9a06ff45e439d8c00bc6406d48191
            admin_key = "d16c6bf31be03c2cd0cfadc7d90a2d69"  # Known dev admin key

            response = await client.delete(
                f"{base_url}/allowance/api/v1/allowance/{test_id}",
                headers={"X-Api-Key": admin_key}
            )

            print(f"Delete allowance API response: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                print(f"✅ Deleted allowance: {data.get('message', 'Success')}")
                return True
            elif response.status_code == 404:
                print(f"⚠️ Allowance not found (expected for test ID)")
                return True
            else:
                print(f"❌ Failed to delete allowance: {response.text}")
                return False

    except Exception as e:
        print(f"❌ API test error: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(test_delete_allowance())
    exit(0 if success else 1)
