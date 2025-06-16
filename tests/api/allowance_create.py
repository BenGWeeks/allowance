"""
API test for POST /api/v1/allowance - Create allowance endpoint
"""

import httpx
import asyncio
from datetime import datetime, timedelta


async def test_create_allowance():
    """Test creating a new allowance via API"""
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

            # Step 1: Get initial count
            initial_response = await client.get(
                f"{base_url}/allowance/api/v1/allowance",
                headers={"X-Api-Key": admin_key},
            )

            if initial_response.status_code != 200:
                print(f"❌ Failed to get initial count: {initial_response.status_code}")
                return False

            initial_count = len(initial_response.json())
            print(f"📊 Initial allowance count: {initial_count}")

            # Step 2: Create allowance
            start_date = datetime.utcnow() + timedelta(days=1)
            payload = {
                "name": "Test API Create Allowance",
                "lightning_address": "test@example.com",
                "amount": 1000,
                "currency": "sats",
                "frequency_type": "daily",
                "start_date": start_date.isoformat(),
                "next_payment_date": start_date.isoformat(),
                "active": True,
                "memo": "Created via API test",
            }

            response = await client.post(
                f"{base_url}/allowance/api/v1/allowance",
                json=payload,
                headers={"X-Api-Key": admin_key},
            )

            print(f"Create allowance API response: {response.status_code}")

            if response.status_code != 201:
                print(f"❌ Failed to create allowance: HTTP {response.status_code}")
                print(f"   Response: {response.text}")
                return False

            data = response.json()
            print(f"✅ Created allowance: {data.get('name')} (ID: {data.get('id')})")

            # Step 3: Verify count increased by 1
            final_response = await client.get(
                f"{base_url}/allowance/api/v1/allowance",
                headers={"X-Api-Key": admin_key},
            )

            if final_response.status_code != 200:
                print(f"❌ Failed to get final count: {final_response.status_code}")
                return False

            final_count = len(final_response.json())
            count_change = final_count - initial_count

            print(f"📊 Final allowance count: {final_count}")
            print(f"📈 Count change: +{count_change}")

            if count_change == 1:
                print("✅ Count verification passed: +1 allowance created")
                return True
            else:
                print(f"❌ Count verification failed: expected +1, got +{count_change}")
                return False

    except Exception as e:
        print(f"❌ API test error: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(test_create_allowance())
    exit(0 if success else 1)
