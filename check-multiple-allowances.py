#!/usr/bin/env python3
"""
Check multiple specific allowances that are losing their datetime values
"""

import httpx
import asyncio
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'tests'))
from get_api_key import get_admin_api_key
from pathlib import Path
from datetime import datetime, timezone

async def check_allowances():
    """Check the specific allowances that are having issues"""

    # IDs to check
    problem_ids = [
        '3PTZjiEouMEybkxZnerqQm',
        'BgvoEqLW2ioVAQXeQuhqTs',
        'JgmbyFCTPWsYz3FNrxW2GS',
        '6wqgxbQs57CtoJsG2NxuS3'
    ]

    # Load config
    env_path = Path(__file__).parent / '.env.local'
    config = {}
    with open(env_path, 'r') as f:
        for line in f:
            if '=' in line and not line.startswith('#'):
                key, value = line.strip().split('=', 1)
                if key == 'TEST_LNBITS_URL':
                    config['base_url'] = value

    admin_key = await get_admin_api_key()

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{config['base_url']}/allowance/api/v1/allowance",
            headers={'X-Api-Key': admin_key}
        )

        if response.status_code == 200:
            allowances = response.json()

            print(f"🔍 Checking {len(problem_ids)} specific allowances:\n")

            for target_id in problem_ids:
                found = False
                for a in allowances:
                    if a['id'] == target_id:
                        found = True
                        print(f"📋 {target_id}:")
                        print(f"  Name: {a.get('name')}")
                        print(f"  Active: {a.get('active')}")
                        print(f"  Start: {a.get('start_datetime', '❌ BLANK')}")
                        print(f"  End: {a.get('end_datetime', '❌ BLANK')}")
                        print(f"  Created: {a.get('created_at')}")
                        print(f"  Frequency: {a.get('frequency_type')}")
                        print(f"  Amount: {a.get('amount')} {a.get('currency')}")
                        print(f"  Total paid: {a.get('total', 0)}")
                        print()
                        break

                if not found:
                    print(f"❌ {target_id}: NOT FOUND\n")

            # Also check for any recently modified allowances
            print("\n🔍 Checking for patterns in ALL allowances:")
            blank_start_count = 0
            blank_end_count = 0
            active_count = 0

            for a in allowances:
                if not a.get('start_datetime'):
                    blank_start_count += 1
                if not a.get('end_datetime'):
                    blank_end_count += 1
                if a.get('active'):
                    active_count += 1

            print(f"  Total allowances: {len(allowances)}")
            print(f"  With blank start_datetime: {blank_start_count}")
            print(f"  With blank end_datetime: {blank_end_count}")
            print(f"  Currently active: {active_count}")

        else:
            print(f"❌ Failed to fetch allowances: {response.status_code}")

if __name__ == "__main__":
    asyncio.run(check_allowances())