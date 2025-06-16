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
        async with httpx.AsyncClient() as client:
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

            # For development testing, we need an actual API key
            # This is the admin key for wallet b2a9a06ff45e439d8c00bc6406d48191
            admin_key = "d16c6bf31be03c2cd0cfadc7d90a2d69"  # Known dev admin key

            response = await client.post(
                f"{base_url}/allowance/api/v1/allowance",
                json=payload,
                headers={"X-Api-Key": admin_key}
            )

            print(f"Create allowance API response: {response.status_code}")

            if response.status_code == 201:
                data = response.json()
                print(
                    f"✅ Created allowance: {data.get('name')} (ID: {data.get('id')})"
                )
                return True
            else:
                print(f"❌ Failed to create allowance: {response.text}")
                return False

    except Exception as e:
        print(f"❌ API test error: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(test_create_allowance())
    exit(0 if success else 1)
