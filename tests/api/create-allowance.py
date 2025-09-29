"""
API test for POST /api/v1/allowance - Create allowance endpoint
"""

import asyncio
import random
from datetime import datetime, timedelta, timezone

import httpx


async def test_create_allowance():  # noqa: C901
    """Test creating a new allowance via API"""
    # Load config from .env.local
    from pathlib import Path

    env_path = Path(__file__).parent.parent.parent / ".env.local"
    config = {}

    if not env_path.exists():
        print(f"❌ .env.local not found at {env_path}")
        return False

    with open(env_path) as f:
        for line in f:
            if "=" in line and not line.startswith("#"):
                key, value = line.strip().split("=", 1)
                if key == "PAYLINK_EMAIL":
                    config["lightning_address"] = value
                elif key == "TEST_LNBITS_URL":
                    config["base_url"] = value

    if "base_url" not in config or "lightning_address" not in config:
        print(
            "❌ Missing required config values in .env.local "
            "(TEST_LNBITS_URL or PAYLINK_EMAIL)"
        )
        return False

    base_url = config["base_url"]

    try:
        # Get admin API key dynamically
        import os
        import sys

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
            start_datetime = datetime.now(timezone.utc) + timedelta(days=1)
            payload = {
                "name": "Test API Create Allowance",
                "lightning_address": config["lightning_address"],
                "amount": random.randint(1, 99),  # Random amount between 1-99 sats
                "currency": "sats",
                "frequency_type": "daily",
                "start_datetime": start_datetime.isoformat(),
                "next_payment_date": start_datetime.isoformat(),
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
