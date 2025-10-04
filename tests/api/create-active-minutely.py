#!/usr/bin/env python3
"""
Create an ACTIVE minutely allowance with proper datetime values
"""

import asyncio
import random
from datetime import datetime, timedelta, timezone

import httpx


async def create_active_minutely():  # noqa: C901
    """Create an active minutely allowance that should start paying immediately"""
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
            # Create active minutely allowance starting 2 minutes from now
            # (Backend requires start_datetime to be at least 1 minute in future,
            # use 2 minutes to ensure buffer for processing time)
            now = datetime.now(timezone.utc)
            start_time = now + timedelta(minutes=2)  # Start 2 minutes from now
            end_time = start_time + timedelta(minutes=3)  # Run for 3 minutes

            # Calculate next payment date (1 minute from start for minutely)
            next_payment = start_time + timedelta(minutes=1)

            test_data = {
                "name": "Test Active Minutely Payment",
                "lightning_address": config["lightning_address"],
                "amount": random.randint(1, 99),  # Random amount between 1-99 sats
                "currency": "sats",
                "frequency_type": "minutely",
                "start_datetime": start_time.isoformat(),
                "end_datetime": end_time.isoformat(),
                "next_payment_date": next_payment.isoformat(),
                "active": True,  # IMPORTANT: Set to active
                "memo": "Active minutely payment test",
            }

            print("📝 Creating ACTIVE minutely allowance:")
            print(f"   Name: {test_data['name']}")
            print(f"   Amount: {test_data['amount']} sats per minute")
            print(f"   Active: {test_data['active']}")
            print(f"   Start: In 2 minutes ({start_time.strftime('%H:%M:%S')})")
            print(f"   End: In 5 minutes ({end_time.strftime('%H:%M:%S')})")
            print(f"   Lightning address: {test_data['lightning_address']}")

            create_response = await client.post(
                f"{base_url}/allowance/api/v1/allowance",
                json=test_data,
                headers={"X-Api-Key": admin_key},
            )

            if create_response.status_code == 201:
                created = create_response.json()
                print("\n✅ Successfully created active minutely allowance!")
                print(f"   ID: {created['id']}")
                print("   Status: ACTIVE ✅")
                print(
                    "\n⏳ Waiting 185 seconds for first payment "
                    "(2 min until start + 1 min frequency + 5 sec buffer)..."
                )

                await asyncio.sleep(185)

                # Check if payment was made
                fetch_response = await client.get(
                    f"{base_url}/allowance/api/v1/allowance",
                    headers={"X-Api-Key": admin_key},
                )

                if fetch_response.status_code == 200:
                    allowances = fetch_response.json()
                    for allowance in allowances:
                        if allowance["id"] == created["id"]:
                            print("\n📊 Allowance status after ~2 minutes:")
                            is_active = "✅" if allowance.get("active") else "❌"
                            print(f"   Active: {is_active}")
                            print(
                                f"   Next payment: {allowance.get('next_payment_date')}"
                            )
                            total = allowance.get("total", 0)
                            if total > 0:
                                print(f"   💰 Total paid: {total} sats ✅")
                                print("\n✅ MINUTELY PAYMENTS ARE WORKING!")
                            else:
                                print("   ⚠️ No payments made yet (total: 0)")
                            break

                return True
            else:
                print(f"❌ Failed to create allowance: {create_response.status_code}")
                print(f"   Response: {create_response.text}")
                return False

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(create_active_minutely())
    exit(0 if success else 1)
