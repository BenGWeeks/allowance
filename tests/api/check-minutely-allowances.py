#!/usr/bin/env python3
"""
Check the status of minutely allowances and why they might not be paying
"""

import httpx
import asyncio
from datetime import datetime, timezone

async def check_minutely_allowances():
    """Check minutely allowances and their payment status"""
    # Load config from .env.local
    from pathlib import Path
    env_path = Path(__file__).parent.parent.parent / '.env.local'
    config = {}

    if not env_path.exists():
        print(f"❌ .env.local not found at {env_path}")
        return False

    with open(env_path, 'r') as f:
        for line in f:
            if '=' in line and not line.startswith('#'):
                key, value = line.strip().split('=', 1)
                if key == 'TEST_LNBITS_URL':
                    config['base_url'] = value

    if 'base_url' not in config:
        print("❌ Missing TEST_LNBITS_URL in .env.local")
        return False

    base_url = config['base_url']

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
            minutely_allowances = [a for a in allowances if a.get('frequency_type') == 'minutely']
            print(f"🕐 Found {len(minutely_allowances)} minutely allowances:\n")

            current_time = datetime.now(timezone.utc)

            for allowance in minutely_allowances:
                print(f"Allowance: {allowance['name']}")
                print(f"  ID: {allowance['id']}")
                print(f"  Amount: {allowance['amount']} {allowance.get('currency', 'sats')}")
                print(f"  Active: {'✅' if allowance.get('active') else '❌'}")
                print(f"  Lightning Address: {allowance.get('lightning_address')}")

                # Check start datetime
                start_dt_str = allowance.get('start_datetime')
                if start_dt_str:
                    try:
                        # Handle microseconds in timestamp
                        if '.' in start_dt_str and len(start_dt_str.split('.')[1]) > 3:
                            # Truncate microseconds to milliseconds
                            start_dt_str = start_dt_str[:start_dt_str.rfind('.')+4]
                        start_dt = datetime.fromisoformat(start_dt_str.replace('Z', '+00:00'))
                        time_until_start = (start_dt - current_time).total_seconds()

                        if time_until_start > 0:
                            print(f"  ⏳ Start time: {start_dt_str} (starts in {int(time_until_start/60)} minutes)")
                        else:
                            print(f"  ✅ Start time: {start_dt_str} (started {int(-time_until_start/60)} minutes ago)")
                    except Exception as e:
                        print(f"  ⚠️ Start time: {start_dt_str} (error parsing: {e})")
                else:
                    print(f"  ✅ Start time: Immediate (no start_datetime set)")

                # Check end datetime
                end_dt_str = allowance.get('end_datetime')
                if end_dt_str:
                    try:
                        if '.' in end_dt_str and len(end_dt_str.split('.')[1]) > 3:
                            end_dt_str = end_dt_str[:end_dt_str.rfind('.')+4]
                        end_dt = datetime.fromisoformat(end_dt_str.replace('Z', '+00:00'))
                        time_until_end = (end_dt - current_time).total_seconds()

                        if time_until_end > 0:
                            print(f"  🏁 End time: {end_dt_str} (ends in {int(time_until_end/60)} minutes)")
                        else:
                            print(f"  ❌ End time: {end_dt_str} (ENDED {int(-time_until_end/60)} minutes ago)")
                    except Exception as e:
                        print(f"  ⚠️ End time: {end_dt_str} (error: {e})")
                else:
                    print(f"  ∞ End time: None (runs indefinitely)")

                # Check next payment date
                next_payment = allowance.get('next_payment_date')
                if next_payment:
                    print(f"  📅 Next payment: {next_payment}")
                else:
                    print(f"  ⚠️ Next payment: Not set")

                # Check total paid (if available)
                total = allowance.get('total', 0)
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
                print(f"ℹ️ Could not get scheduler status (endpoint may not exist)")

            return True

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(check_minutely_allowances())
    exit(0 if success else 1)