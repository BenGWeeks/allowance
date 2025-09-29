"""
API test for DELETE /api/v1/allowance/{id} - Delete allowance endpoint
"""

import asyncio

import httpx


async def test_delete_allowance():  # noqa: C901
    """Test deleting an allowance via API - proper test with count verification"""
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
        from datetime import datetime, timedelta, timezone

        from get_api_key import get_admin_api_key

        admin_key = await get_admin_api_key()
        if not admin_key:
            print("❌ Failed to get admin API key")
            return False

        async with httpx.AsyncClient() as client:

            # Step 1: Count allowances before
            response = await client.get(
                f"{base_url}/allowance/api/v1/allowance",
                headers={"X-Api-Key": admin_key},
            )

            if response.status_code != 200:
                print(f"❌ Failed to get allowances: {response.status_code}")
                return False

            initial_count = len(response.json())
            print(f"📊 Initial allowance count: {initial_count}")

            # Step 2: Create a test allowance to delete
            create_data = {
                "name": "TEST_DELETE_ALLOWANCE",
                "lightning_address": config["lightning_address"],
                "amount": 1,
                "currency": "sats",
                "frequency_type": "weekly",
                "start_datetime": datetime.now(timezone.utc).isoformat(),
                "next_payment_date": (
                    datetime.now(timezone.utc) + timedelta(days=7)
                ).isoformat(),
                "active": True,
                "memo": "Test allowance for deletion",
            }

            create_response = await client.post(
                f"{base_url}/allowance/api/v1/allowance",
                json=create_data,
                headers={"X-Api-Key": admin_key},
            )

            if create_response.status_code != 201:
                print(
                    f"❌ Failed to create test allowance: {create_response.status_code}"
                )
                return False

            created_allowance = create_response.json()
            test_id = created_allowance["id"]
            print(f"✅ Created test allowance: {test_id}")

            # Step 3: Delete the test allowance
            delete_response = await client.delete(
                f"{base_url}/allowance/api/v1/allowance/{test_id}",
                headers={"X-Api-Key": admin_key},
            )

            print(f"Delete allowance API response: {delete_response.status_code}")

            if delete_response.status_code != 200:
                print(
                    f"❌ Failed to delete allowance: HTTP {delete_response.status_code}"
                )
                print(f"   Response: {delete_response.text}")
                return False

            print(f"✅ Deleted allowance: {test_id}")

            # Step 4: Verify count decreased by 1
            final_response = await client.get(
                f"{base_url}/allowance/api/v1/allowance",
                headers={"X-Api-Key": admin_key},
            )

            if final_response.status_code != 200:
                print(
                    f"❌ Failed to get final allowances: {final_response.status_code}"
                )
                return False

            final_count = len(final_response.json())
            print(f"📊 Final allowance count: {final_count}")

            if final_count == initial_count:
                print(f"✅ Count verification passed: {initial_count} -> {final_count}")
                return True
            else:
                print(
                    f"❌ Count verification failed: expected {initial_count}, "
                    f"got {final_count}"
                )
                return False

    except Exception as e:
        print(f"❌ API test error: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(test_delete_allowance())
    exit(0 if success else 1)
