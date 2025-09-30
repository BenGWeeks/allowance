#!/usr/bin/env python3
"""
Test that scheduler properly deactivates expired allowances and they stay deactivated.
This test catches the bug where expired allowances keep appearing as active.
"""

import asyncio
import random
from datetime import datetime, timedelta, timezone

import httpx


async def test_scheduler_deactivation():  # noqa: C901
    """Test that scheduler deactivation persists properly"""
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
        print("❌ Missing required config values in .env.local")
        return False

    # Use base URL from config
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
            # Create an allowance that will expire in 1 minute
            now = datetime.now(timezone.utc)
            end_time = now + timedelta(seconds=70)  # Expires in 70 seconds

            test_data = {
                "name": "Test Deactivation Check",
                "lightning_address": config["lightning_address"],
                "amount": random.randint(1, 99),  # Random amount between 1-99 sats
                "currency": "sats",
                "frequency_type": "minutely",
                "start_datetime": now.isoformat(),
                "end_datetime": end_time.isoformat(),
                "next_payment_date": (now + timedelta(minutes=1)).isoformat(),
                "active": True,
                "memo": "Testing scheduler deactivation",
            }

            print("📝 Creating test allowance that expires in 70 seconds...")
            create_response = await client.post(
                f"{base_url}/allowance/api/v1/allowance",
                json=test_data,
                headers={"X-Api-Key": admin_key},
            )

            if create_response.status_code != 201:
                print(
                    f"❌ Failed to create test allowance: {create_response.status_code}"
                )
                return False

            created = create_response.json()
            test_id = created["id"]
            print(f"✅ Created test allowance: {test_id}")
            print(f"   Will expire at: {end_time.strftime('%H:%M:%S')}")

            # Wait for it to expire and for scheduler to run
            # Scheduler runs every 60 seconds, so wait 130 seconds to ensure:
            # - Allowance expires at 70 seconds
            # - Scheduler has time to run (next cycle could be up to 60s away)
            # - Total: 70 + 60 = 130 seconds minimum
            print(
                "⏳ Waiting 130 seconds for allowance to expire and scheduler "
                "to deactivate it..."
            )
            await asyncio.sleep(130)

            # Now check the status multiple times over 2 minutes to confirm it
            # stays deactivated
            print("\n🔍 Checking if allowance stays deactivated over 2 minutes...")

            deactivation_checks = []
            for minute in range(2):
                await asyncio.sleep(
                    60 if minute > 0 else 0
                )  # Wait 1 minute between checks

                # Fetch the allowance
                response = await client.get(
                    f"{base_url}/allowance/api/v1/allowance",
                    headers={"X-Api-Key": admin_key},
                )

                if response.status_code == 200:
                    allowances = response.json()
                    for a in allowances:
                        if a["id"] == test_id:
                            is_active = a.get("active", False)
                            deactivation_checks.append(
                                {
                                    "minute": minute + 1,
                                    "active": is_active,
                                    "start_datetime": a.get("start_datetime"),
                                    "end_datetime": a.get("end_datetime"),
                                }
                            )

                            print(
                                f"   Minute {minute + 1}: Active={is_active}, "
                                f"Start={a.get('start_datetime', 'NONE')}, "
                                f"End={a.get('end_datetime', 'NONE')}"
                            )
                            break

            # Analyze results
            print("\n📊 Test Results:")
            all_inactive = all(not check["active"] for check in deactivation_checks)
            datetimes_preserved = all(
                check["start_datetime"] and check["end_datetime"]
                for check in deactivation_checks
            )

            if all_inactive:
                num_checks = len(deactivation_checks)
                print(f"✅ Allowance stayed inactive for all {num_checks} checks")
            else:
                active_checks = [c for c in deactivation_checks if c["active"]]
                num_active = len(active_checks)
                print(
                    f"❌ BUG DETECTED: Allowance was active in {num_active} "
                    f"checks after expiry!"
                )
                for check in active_checks:
                    print(f"   Minute {check['minute']}: Was incorrectly ACTIVE")

            if datetimes_preserved:
                print("✅ Datetime fields preserved in all checks")
            else:
                missing_checks = [
                    c
                    for c in deactivation_checks
                    if not c["start_datetime"] or not c["end_datetime"]
                ]
                print(f"❌ Datetime fields missing in {len(missing_checks)} checks!")

            # Clean up
            await client.delete(
                f"{base_url}/allowance/api/v1/allowance/{test_id}",
                headers={"X-Api-Key": admin_key},
            )

            return all_inactive and datetimes_preserved

    except Exception as e:
        print(f"❌ Test error: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("🧪 Testing scheduler deactivation persistence")
    print("=" * 60)
    success = asyncio.run(test_scheduler_deactivation())

    if success:
        print("\n✅ Scheduler deactivation test PASSED")
    else:
        print("\n❌ Scheduler deactivation test FAILED - Bug detected!")

    exit(0 if success else 1)
