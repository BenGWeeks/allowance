#!/usr/bin/env python3
"""
Create an ACTIVE minutely allowance with proper datetime values
"""

import httpx
import asyncio
from datetime import datetime, timedelta, timezone


async def create_active_minutely():
    """Create an active minutely allowance that should start paying immediately"""
    # Load config from .env.local
    from pathlib import Path

    env_path = Path(__file__).parent.parent.parent / ".env.local"
    config = {}

    if not env_path.exists():
        print(f"❌ .env.local not found at {env_path}")
        return False

    with open(env_path, "r") as f:
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
        import sys
        import os

        sys.path.append(os.path.dirname(os.path.dirname(__file__)))
        from get_api_key import get_admin_api_key

        admin_key = await get_admin_api_key()
        if not admin_key:
            print("❌ Failed to get admin API key")
            return False

        async with httpx.AsyncClient() as client:
            # Create active minutely allowance starting NOW
            now = datetime.now(timezone.utc)
            end_time = now + timedelta(minutes=10)  # Run for 10 minutes

            # Calculate next payment date (1 minute from now for minutely)
            next_payment = now + timedelta(minutes=1)

            test_data = {
                "name": f"ACTIVE_Minutely_Test_{int(now.timestamp())}",
                "lightning_address": config["lightning_address"],
                "amount": 2,  # 2 sats per minute
                "currency": "sats",
                "frequency_type": "minutely",
                "start_datetime": now.isoformat(),
                "end_datetime": end_time.isoformat(),
                "next_payment_date": next_payment.isoformat(),
                "active": True,  # IMPORTANT: Set to active
                "memo": "Active minutely payment test",
            }

            print(f"📝 Creating ACTIVE minutely allowance:")
            print(f"   Name: {test_data['name']}")
            print(f"   Amount: {test_data['amount']} sats per minute")
            print(f"   Active: {test_data['active']}")
            print(f"   Start: NOW ({now.strftime('%H:%M:%S')})")
            print(f"   End: In 10 minutes ({end_time.strftime('%H:%M:%S')})")
            print(f"   Lightning address: {test_data['lightning_address']}")

            create_response = await client.post(
                f"{base_url}/allowance/api/v1/allowance",
                json=test_data,
                headers={"X-Api-Key": admin_key},
            )

            if create_response.status_code == 201:
                created = create_response.json()
                print(f"\n✅ Successfully created active minutely allowance!")
                print(f"   ID: {created['id']}")
                print(f"   Status: ACTIVE ✅")
                print(f"\n⏳ Waiting 65 seconds for first payment...")

                await asyncio.sleep(65)

                # Check if payment was made
                fetch_response = await client.get(
                    f"{base_url}/allowance/api/v1/allowance",
                    headers={"X-Api-Key": admin_key},
                )

                if fetch_response.status_code == 200:
                    allowances = fetch_response.json()
                    for allowance in allowances:
                        if allowance["id"] == created["id"]:
                            print(f"\n📊 Allowance status after 1 minute:")
                            print(
                                f"   Active: {'✅' if allowance.get('active') else '❌'}"
                            )
                            print(
                                f"   Next payment: {allowance.get('next_payment_date')}"
                            )
                            total = allowance.get("total", 0)
                            if total > 0:
                                print(f"   💰 Total paid: {total} sats ✅")
                                print(f"\n✅ MINUTELY PAYMENTS ARE WORKING!")
                            else:
                                print(f"   ⚠️ No payments made yet (total: 0)")
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
