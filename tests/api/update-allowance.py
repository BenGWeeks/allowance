"""
API test for PUT /api/v1/allowance/{id} - Update allowance endpoint
"""

import asyncio
from datetime import datetime, timedelta, timezone

import httpx


async def test_update_allowance():  # noqa: C901
    """Test updating an allowance via API - proper test with create→update→verify"""
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

            # Step 1: Create a test allowance to update
            start_datetime = datetime.now(timezone.utc) + timedelta(days=1)
            create_data = {
                "name": "TEST_UPDATE_ALLOWANCE",
                "lightning_address": config["lightning_address"],
                "amount": 10,  # Small amount < 100 sats
                "currency": "sats",
                "frequency_type": "weekly",
                "start_datetime": start_datetime.isoformat(),
                "next_payment_date": (start_datetime + timedelta(days=7)).isoformat(),
                "active": True,
                "memo": "Test allowance for update",
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

            # Step 2: Update the allowance
            update_start_datetime = datetime.now(timezone.utc) + timedelta(days=2)
            update_data = {
                "name": "Test Updated Allowance",
                "lightning_address": config["lightning_address"],
                "amount": 20,  # Updated small amount < 100 sats
                "currency": "sats",
                "frequency_type": "monthly",
                "start_datetime": update_start_datetime.isoformat(),
                "next_payment_date": (
                    update_start_datetime + timedelta(days=30)
                ).isoformat(),
                "active": False,
                "memo": "Updated via API test",
            }

            update_response = await client.put(
                f"{base_url}/allowance/api/v1/allowance/{test_id}",
                json=update_data,
                headers={"X-Api-Key": admin_key},
            )

            print(f"Update allowance API response: {update_response.status_code}")

            if update_response.status_code != 200:
                print(
                    f"❌ Failed to update allowance: HTTP {update_response.status_code}"
                )
                print(f"   Response: {update_response.text}")
                return False

            print(f"✅ Updated allowance: {test_id}")

            # Step 3: Verify the update by fetching the allowance
            list_response = await client.get(
                f"{base_url}/allowance/api/v1/allowance",
                headers={"X-Api-Key": admin_key},
            )

            if list_response.status_code != 200:
                print(f"❌ Failed to fetch allowances: {list_response.status_code}")
                return False

            allowances = list_response.json()
            updated_allowance = None
            for allowance in allowances:
                if allowance["id"] == test_id:
                    updated_allowance = allowance
                    break

            if not updated_allowance:
                print("❌ Updated allowance not found")
                return False

            # Verify the updates
            success = True
            if updated_allowance["name"] != "Test Updated Allowance":
                actual_name = updated_allowance["name"]
                print(
                    f"❌ Name not updated: expected 'Test Updated Allowance', "
                    f"got '{actual_name}'"
                )
                success = False
            if updated_allowance["lightning_address"] != config["lightning_address"]:
                expected_addr = config["lightning_address"]
                actual_addr = updated_allowance["lightning_address"]
                print(
                    f"❌ Address not updated: expected '{expected_addr}', "
                    f"got '{actual_addr}'"
                )
                success = False
            if updated_allowance["amount"] != 20:
                actual_amount = updated_allowance["amount"]
                print(f"❌ Amount not updated: expected 20, got {actual_amount}")
                success = False
            if updated_allowance["active"] is not False:
                actual_active = updated_allowance["active"]
                print(
                    f"❌ Active status not updated: expected False, "
                    f"got {actual_active}"
                )
                success = False

            # Verify datetime fields are present and updated
            if "start_datetime" not in updated_allowance:
                print("❌ start_datetime field missing from response")
                success = False
            else:
                print(
                    f"✅ start_datetime present: {updated_allowance['start_datetime']}"
                )

            if updated_allowance.get("end_datetime"):
                print(f"✅ end_datetime present: {updated_allowance['end_datetime']}")
            else:
                print("ℹ️ end_datetime not set (optional field)")  # noqa: RUF001

            if success:
                print("✅ All update verifications passed")
                return True
            else:
                print("❌ Some update verifications failed")
                return False

    except Exception as e:
        print(f"❌ API test error: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(test_update_allowance())
    exit(0 if success else 1)
