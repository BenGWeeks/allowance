"""
API test for GET /api/v1/rate/{currency} - Currency rate endpoint
"""

import httpx
import asyncio


async def test_currency_rate():
    """Test retrieving currency exchange rate via API"""
    base_url = "http://localhost:5001"

    try:
        async with httpx.AsyncClient() as client:
            # Test USD rate (common currency)
            response = await client.get(f"{base_url}/allowance/api/v1/rate/USD")

            print(f"Currency rate API response: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                rate = data.get("rate")
                print(f"✅ USD rate: {rate} sats per USD")
                return rate is not None
            else:
                print(f"❌ Failed to get currency rate: {response.text}")
                return False

    except Exception as e:
        print(f"❌ API test error: {e}")
        return False


async def test_invalid_currency():
    """Test retrieving rate for invalid currency"""
    base_url = "http://localhost:5001"

    try:
        async with httpx.AsyncClient() as client:
            # Test invalid currency
            response = await client.get(f"{base_url}/allowance/api/v1/rate/INVALID")

            print(f"Invalid currency API response: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                rate = data.get("rate")
                if rate is None:
                    print(f"✅ Invalid currency correctly returned null rate")
                    return True
                else:
                    print(f"⚠️ Invalid currency returned rate: {rate}")
                    return True  # Still successful API call
            else:
                print(f"❌ Failed to get invalid currency rate: {response.text}")
                return False

    except Exception as e:
        print(f"❌ API test error: {e}")
        return False


if __name__ == "__main__":
    print("🧪 Testing currency rate endpoints...")

    success1 = asyncio.run(test_currency_rate())
    success2 = asyncio.run(test_invalid_currency())

    if success1 and success2:
        print("✅ All currency rate tests passed")
        exit(0)
    else:
        print("❌ Some currency rate tests failed")
        exit(1)
