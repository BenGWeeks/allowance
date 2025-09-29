#!/usr/bin/env python3
"""
Check the status of minutely allowances and why they might not be paying
"""

import asyncio
from datetime import datetime, timezone

import httpx


async def check_minutely_allowances():  # noqa: C901
    """Check minutely allowances and their payment status"""
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
                if key == "TEST_LNBITS_URL":
                    config["base_url"] = value

    if "base_url" not in config:
        print("❌ Missing TEST_LNBITS_URL in .env.local")
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
            # Get all allowances
            response = await client.get(
                f"{base_url}/allowance/api/v1/allowance",
                headers={"X-Api-Key": admin_key},
            )

            if response.status_code != 200:
                print(f"❌ Failed to fetch allowances: {response.status_code}")
                return False

            allowances = response.json()
            print(f"📊 Found {len(allowances)} total allowances\n")

            # Filter for minutely allowances
            minutely_allowances = [
                a for a in allowances if a.get("frequency_type") == "minutely"
            ]
            print(f"🕐 Found {len(minutely_allowances)} minutely allowances:\n")

            current_time = datetime.now(timezone.utc)

            for allowance in minutely_allowances:
                print(f"Allowance: {allowance['name']}")
                print(f"  ID: {allowance['id']}")
                amount = allowance["amount"]
                currency = allowance.get("currency", "sats")
                print(f"  Amount: {amount} {currency}")
                print(f"  Active: {'✅' if allowance.get('active') else '❌'}")
                print(f"  Lightning Address: {allowance.get('lightning_address')}")

                # Check start datetime
                start_dt_str = allowance.get("start_datetime")
                if start_dt_str:
                    try:
                        # Handle microseconds in timestamp
                        if "." in start_dt_str and len(start_dt_str.split(".")[1]) > 3:
                            # Truncate microseconds to milliseconds
                            start_dt_str = start_dt_str[: start_dt_str.rfind(".") + 4]
                        start_dt = datetime.fromisoformat(
                            start_dt_str.replace("Z", "+00:00")
                        )
                        time_until_start = (start_dt - current_time).total_seconds()

                        if time_until_start > 0:
                            mins_to_start = int(time_until_start / 60)
                            print(
                                f"  ⏳ Start time: {start_dt_str} "
                                f"(starts in {mins_to_start} minutes)"
                            )
                        else:
                            mins_since_start = int(-time_until_start / 60)
                            print(
                                f"  ✅ Start time: {start_dt_str} "
                                f"(started {mins_since_start} minutes ago)"
                            )
                    except Exception as e:
                        print(f"  ⚠️ Start time: {start_dt_str} (error parsing: {e})")
                else:
                    print("  ✅ Start time: Immediate (no start_datetime set)")

                # Check end datetime
                end_dt_str = allowance.get("end_datetime")
                if end_dt_str:
                    try:
                        if "." in end_dt_str and len(end_dt_str.split(".")[1]) > 3:
                            end_dt_str = end_dt_str[: end_dt_str.rfind(".") + 4]
                        end_dt = datetime.fromisoformat(
                            end_dt_str.replace("Z", "+00:00")
                        )
                        time_until_end = (end_dt - current_time).total_seconds()

                        if time_until_end > 0:
                            mins_to_end = int(time_until_end / 60)
                            print(
                                f"  🏁 End time: {end_dt_str} "
                                f"(ends in {mins_to_end} minutes)"
                            )
                        else:
                            mins_since_end = int(-time_until_end / 60)
                            print(
                                f"  ❌ End time: {end_dt_str} "
                                f"(ENDED {mins_since_end} minutes ago)"
                            )
                    except Exception as e:
                        print(f"  ⚠️ End time: {end_dt_str} (error: {e})")
                else:
                    print("  ∞ End time: None (runs indefinitely)")

                # Check next payment date
                next_payment = allowance.get("next_payment_date")
                if next_payment:
                    print(f"  📅 Next payment: {next_payment}")
                else:
                    print("  ⚠️ Next payment: Not set")

                # Check total paid (if available)
                total = allowance.get("total", 0)
                if total:
                    print(f"  💰 Total paid so far: {total} sats")

                print()

            # Check if scheduler is running
            print("\n🔍 Checking scheduler status...")

            # Try to get scheduler logs or status
            scheduler_response = await client.get(
                f"{base_url}/allowance/api/v1/scheduler/status",
                headers={"X-Api-Key": admin_key},
            )

            if scheduler_response.status_code == 200:
                scheduler_status = scheduler_response.json()
                print(f"✅ Scheduler status: {scheduler_status}")
            else:
                print(
                    "ℹ️ Could not get scheduler status (endpoint may not exist)"  # noqa: RUF001
                )

            return True

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(check_minutely_allowances())
    exit(0 if success else 1)
