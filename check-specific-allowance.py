#!/usr/bin/env python3
"""
Check a specific allowance by ID
"""

import httpx
import asyncio
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "tests"))
from get_api_key import get_admin_api_key
from pathlib import Path


async def check_specific_allowance():
    """Check the specific allowance that's having issues"""

    # Load config
    env_path = Path(__file__).parent / ".env.local"
    config = {}
    with open(env_path, "r") as f:
        for line in f:
            if "=" in line and not line.startswith("#"):
                key, value = line.strip().split("=", 1)
                if key == "TEST_LNBITS_URL":
                    config["base_url"] = value

    admin_key = await get_admin_api_key()

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{config['base_url']}/allowance/api/v1/allowance",
            headers={"X-Api-Key": admin_key},
        )

        if response.status_code == 200:
            allowances = response.json()
            found = False

            for a in allowances:
                if a["id"] == "3PTZjiEouMEybkxZnerqQm":
                    found = True
                    print("📋 Found allowance 3PTZjiEouMEybkxZnerqQm:")
                    print(f"  Name: {a.get('name')}")
                    print(f"  Active: {a.get('active')}")
                    print(f"  Start datetime: {a.get('start_datetime', 'Not set')}")
                    print(f"  End datetime: {a.get('end_datetime', 'Not set')}")
                    print(f"  Created at: {a.get('created_at')}")
                    print(f"  Next payment: {a.get('next_payment_date')}")
                    print(f"  Frequency: {a.get('frequency_type')}")
                    print(f"  Amount: {a.get('amount')} {a.get('currency')}")
                    print(f"  Total paid: {a.get('total', 0)}")

                    # Check if it should be running
                    from datetime import datetime, timezone

                    now = datetime.now(timezone.utc)

                    if a.get("start_datetime"):
                        start = datetime.fromisoformat(
                            a["start_datetime"].replace("Z", "+00:00")
                        )
                        if now < start:
                            print(
                                f"  ⏳ Status: Not started yet (starts in {int((start - now).total_seconds()/60)} minutes)"
                            )
                        else:
                            print(
                                f"  ✅ Status: Started {int((now - start).total_seconds()/60)} minutes ago"
                            )
                    else:
                        print(f"  ✅ Status: No start time set (runs immediately)")

                    if a.get("end_datetime"):
                        end = datetime.fromisoformat(
                            a["end_datetime"].replace("Z", "+00:00")
                        )
                        if now > end:
                            print(
                                f"  🛑 Status: Expired {int((now - end).total_seconds()/60)} minutes ago"
                            )
                        else:
                            print(
                                f"  ⏰ Status: Ends in {int((end - now).total_seconds()/60)} minutes"
                            )
                    else:
                        print(f"  ♾️ Status: No end time set (runs indefinitely)")

                    return

            if not found:
                print("❌ Allowance 3PTZjiEouMEybkxZnerqQm not found in list")
                print(f"📋 Found {len(allowances)} allowances total:")
                for a in allowances[:5]:  # Show first 5
                    print(f"  - {a['id']}: {a.get('name')}")
        else:
            print(f"❌ Failed to fetch allowances: {response.status_code}")


if __name__ == "__main__":
    asyncio.run(check_specific_allowance())
