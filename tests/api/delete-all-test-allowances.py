#!/usr/bin/env python3
"""
Delete all test allowances via API
Deletes only allowances with "Test" or "TEST" in their name
"""

import asyncio
import os
import sys
from pathlib import Path

import httpx

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from get_api_key import get_admin_api_key


async def delete_all_test_allowances():  # noqa: C901
    """Delete all allowances with 'Test' or 'TEST' in the name"""
    # Load config from .env.local
    env_path = Path(__file__).parent.parent.parent / ".env.local"
    config = {}

    if not env_path.exists():
        print(f"❌ .env.local not found at {env_path}")
        return False

    with open(env_path) as f:
        for line in f:
            if "=" in line and not line.startswith("#"):
                key, value = line.strip().split("=", 1)
                if key == "TEST_LNBITS_URL":
                    config["base_url"] = value

    if "base_url" not in config:
        print("❌ Missing TEST_LNBITS_URL in .env.local")
        return False

    base_url = config["base_url"]

    try:
        # Get admin API key dynamically
        admin_key = await get_admin_api_key()
        if not admin_key:
            print("❌ Failed to get admin API key")
            return False

        async with httpx.AsyncClient() as client:
            # Step 1: Get all allowances
            response = await client.get(
                f"{base_url}/allowance/api/v1/allowance",
                headers={"X-Api-Key": admin_key},
            )

            if response.status_code != 200:
                print(f"❌ Failed to get allowances: {response.status_code}")
                return False

            allowances = response.json()
            print(f"📊 Total allowances found: {len(allowances)}")

            # Step 2: Filter test allowances
            test_allowances = [
                a
                for a in allowances
                if "Test" in a.get("name", "") or "TEST" in a.get("name", "")
            ]

            if not test_allowances:
                print("✅ No test allowances to delete")
                return True

            print(f"🎯 Found {len(test_allowances)} test allowance(s) to delete:")
            for allowance in test_allowances:
                print(f"   - {allowance['name']} (ID: {allowance['id']})")

            # Step 3: Delete each test allowance
            deleted_count = 0
            failed_count = 0

            for allowance in test_allowances:
                allowance_id = allowance["id"]
                allowance_name = allowance["name"]

                print(f"\n🗑️  Deleting: {allowance_name}...")

                delete_response = await client.delete(
                    f"{base_url}/allowance/api/v1/allowance/{allowance_id}",
                    headers={"X-Api-Key": admin_key},
                )

                if delete_response.status_code == 200:
                    print(f"   ✅ Deleted successfully")
                    deleted_count += 1
                else:
                    print(
                        f"   ❌ Failed to delete (HTTP {delete_response.status_code})"
                    )
                    print(f"      Response: {delete_response.text}")
                    failed_count += 1

            # Step 4: Verify deletion
            print("\n" + "=" * 60)
            print("📊 Deletion Summary:")
            print(f"   Total test allowances found: {len(test_allowances)}")
            print(f"   Successfully deleted: {deleted_count}")
            print(f"   Failed to delete: {failed_count}")

            # Get final count to verify
            final_response = await client.get(
                f"{base_url}/allowance/api/v1/allowance",
                headers={"X-Api-Key": admin_key},
            )

            if final_response.status_code == 200:
                final_allowances = final_response.json()
                remaining_test = [
                    a
                    for a in final_allowances
                    if "Test" in a.get("name", "") or "TEST" in a.get("name", "")
                ]

                if remaining_test:
                    print(
                        f"\n⚠️  {len(remaining_test)} test allowance(s) still remain:"
                    )
                    for a in remaining_test:
                        print(f"   - {a['name']} (ID: {a['id']})")
                else:
                    print("\n✅ All test allowances deleted successfully!")

                print(f"\n📊 Final total allowance count: {len(final_allowances)}")

            return deleted_count > 0 and failed_count == 0

    except Exception as e:
        print(f"❌ Error deleting test allowances: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("🧹 Delete All Test Allowances via API")
    print("=" * 60)

    success = asyncio.run(delete_all_test_allowances())
    exit(0 if success else 1)