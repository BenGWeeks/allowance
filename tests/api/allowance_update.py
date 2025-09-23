"""
API test for PUT /api/v1/allowance/{id} - Update allowance endpoint
"""

import httpx
import asyncio
from datetime import datetime, timedelta, timezone


async def test_update_allowance():
    """Test updating an allowance via API - proper test with create→update→verify"""
    base_url = "https://lnbits-allowance.weeksfamily.me"

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

            # Step 1: Create a test allowance to update
            start_datetime = datetime.now(timezone.utc) + timedelta(days=1)
            create_data = {
                "name": "TEST_UPDATE_ALLOWANCE",
                "lightning_address": "update-test@example.com",
                "amount": 1000,
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
                "name": "Updated Test Allowance",
                "lightning_address": "updated@example.com",
                "amount": 2000,
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
                print(f"❌ Updated allowance not found")
                return False

            # Verify the updates
            success = True
            if updated_allowance["name"] != "Updated Test Allowance":
                print(
                    f"❌ Name not updated: expected 'Updated Test Allowance', got '{updated_allowance['name']}'"
                )
                success = False
            if updated_allowance["lightning_address"] != "updated@example.com":
                print(
                    f"❌ Address not updated: expected 'updated@example.com', got '{updated_allowance['lightning_address']}'"
                )
                success = False
            if updated_allowance["amount"] != 2000:
                print(
                    f"❌ Amount not updated: expected 2000, got {updated_allowance['amount']}"
                )
                success = False
            if updated_allowance["active"] != False:
                print(
                    f"❌ Active status not updated: expected False, got {updated_allowance['active']}"
                )
                success = False

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
