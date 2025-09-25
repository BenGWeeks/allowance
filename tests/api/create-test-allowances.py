#!/usr/bin/env python3
"""
Create 10 test allowances via API matching the UI test data
This script creates allowances with various configurations including different end dates
"""

import httpx
import asyncio
import json
import os
from datetime import datetime, timedelta
from pathlib import Path

# Load environment variables
def load_config():
    env_path = Path(__file__).parent.parent.parent / '.env.local'
    config = {}

    if not env_path.exists():
        raise Exception(f"Environment file not found: {env_path}")

    with open(env_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                config[key.strip()] = value.strip()

    # Validate required variables
    required = ['TEST_LNBITS_URL', 'LNBITS_ADMIN_USERNAME', 'LNBITS_ADMIN_PASSWORD']
    missing = [key for key in required if key not in config]
    if missing:
        raise Exception(f"Missing required environment variables: {', '.join(missing)}")

    return {
        'base_url': config['TEST_LNBITS_URL'],
        'username': config['LNBITS_ADMIN_USERNAME'],
        'password': config['LNBITS_ADMIN_PASSWORD'],
        'receiving_email': config.get('PAYLINK_EMAIL', 'receiving@lnbits-allowance.weeksfamily.me')
    }

async def get_admin_key(config):
    """Get the admin key for the wallet"""
    async with httpx.AsyncClient() as client:
        # First, we need to find the wallet ID and admin key
        # This would normally be done via login, but for testing we'll use a known key
        # You may need to update this with your actual admin key

        # For now, return the known admin key from the database query
        return "2c3cd50a44784f19a4d7b4f605bbe247"

async def create_allowance(client, base_url, api_key, allowance_data):
    """Create a single allowance"""
    try:
        response = await client.post(
            f"{base_url}/allowance/api/v1/allowance",
            json=allowance_data,
            headers={'X-Api-Key': api_key}
        )

        if response.status_code == 201 or response.status_code == 200:
            print(f"✅ Created: {allowance_data['name']}")
            return True
        else:
            print(f"❌ Failed to create {allowance_data['name']}: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error creating {allowance_data['name']}: {e}")
        return False

async def main():
    config = load_config()
    api_key = await get_admin_key(config)

    print(f"🚀 Creating test allowances via API...")
    print(f"📍 Server: {config['base_url']}")

    # Get current time (use timezone-aware datetime)
    from datetime import timezone
    now = datetime.now(timezone.utc)

    # Define test allowances matching the screenshot
    test_allowances = [
        {
            "name": "Test 1 (API)",
            "lightning_address": "receiving@lnbits-allowance.weeksfamily.me",
            "amount": 1,
            "currency": "sats",
            "frequency_type": "minutely",
            "start_datetime": now.isoformat(),
            "memo": "Test 1 (API)",
            "active": True,
            "end_datetime": (now + timedelta(days=7)).isoformat()  # Future
        },
        {
            "name": "Test 2 (API)",
            "lightning_address": "receiving@lnbits-allowance.weeksfamily.me",
            "amount": 0.02,
            "currency": "GBP",
            "frequency_type": "minutely",
            "start_datetime": (now - timedelta(days=3)).isoformat(),
            "memo": "Test 2 (API)",
            "active": True,
            "end_datetime": None  # No end date
        },
        {
            "name": "Test 3 (API)",
            "lightning_address": "receiving@lnbits-allowance.weeksfamily.me",
            "amount": 0.30,
            "currency": "USD",
            "frequency_type": "minutely",
            "start_datetime": (now - timedelta(days=2, hours=12)).isoformat(),
            "memo": "Test 3 (API)",
            "active": True,
            "end_datetime": (now - timedelta(hours=2)).isoformat()  # Past (should auto-deactivate)
        },
        {
            "name": "Test 4 (API)",
            "lightning_address": "receiving@lnbits-allowance.weeksfamily.me",
            "amount": 4,
            "currency": "sats",
            "frequency_type": "minutely",
            "start_datetime": now.isoformat(),
            "memo": "Test 4 (API)",
            "active": True,
            "end_datetime": (now + timedelta(hours=12)).isoformat()  # Future (today)
        },
        {
            "name": "Test 5 (API)",
            "lightning_address": "receiving@lnbits-allowance.weeksfamily.me",
            "amount": 5,
            "currency": "sats",
            "frequency_type": "minutely",
            "start_datetime": now.isoformat(),
            "memo": "Test 5 (API)",
            "active": True,
            "end_datetime": None  # No end date
        },
        {
            "name": "Test 6 (API)",
            "lightning_address": "receiving@lnbits-allowance.weeksfamily.me",
            "amount": 6,
            "currency": "sats",
            "frequency_type": "minutely",
            "start_datetime": now.isoformat(),
            "memo": "Test 6 (API)",
            "active": True,
            "end_datetime": (now - timedelta(days=1)).isoformat()  # Past (should auto-deactivate)
        },
        {
            "name": "Test 7 (API)",
            "lightning_address": "receiving@lnbits-allowance.weeksfamily.me",
            "amount": 7,
            "currency": "sats",
            "frequency_type": "minutely",
            "start_datetime": (now - timedelta(hours=13)).isoformat(),
            "memo": "Test 7 (API)",
            "active": True,
            "end_datetime": (now + timedelta(hours=11)).isoformat()  # Future (today)
        },
        {
            "name": "Test 8 (API)",
            "lightning_address": "receiving@lnbits-allowance.weeksfamily.me",
            "amount": 8,
            "currency": "sats",
            "frequency_type": "hourly",  # Different frequency
            "start_datetime": now.isoformat(),
            "memo": "Test 8 (API)",
            "active": True,
            "end_datetime": (now + timedelta(days=30)).isoformat()  # Future (next month)
        },
        {
            "name": "Test 9 (API)",
            "lightning_address": "receiving@lnbits-allowance.weeksfamily.me",
            "amount": 9,
            "currency": "sats",
            "frequency_type": "monthly",  # Different frequency
            "start_datetime": now.isoformat(),
            "memo": "Test 9 (API)",
            "active": True,
            "end_datetime": None  # No end date
        },
        {
            "name": "Test 10 (API)",
            "lightning_address": "receiving@lnbits-allowance.weeksfamily.me",
            "amount": 10,
            "currency": "sats",
            "frequency_type": "yearly",  # Different frequency
            "start_datetime": (now + timedelta(hours=12)).isoformat(),  # Future start
            "memo": "Test 10 (API)",
            "active": True,
            "end_datetime": (now + timedelta(days=365)).isoformat()  # Future (next year)
        }
    ]

    success_count = 0

    async with httpx.AsyncClient(timeout=30.0) as client:
        print(f"\n📝 Creating {len(test_allowances)} test allowances...")

        for i, allowance in enumerate(test_allowances, 1):
            print(f"\n[{i}/{len(test_allowances)}] Creating: {allowance['name']}")
            print(f"   Amount: {allowance['amount']} {allowance['currency']}")
            print(f"   Frequency: {allowance['frequency_type']}")

            if allowance['end_datetime']:
                end_dt = datetime.fromisoformat(allowance['end_datetime'].replace('Z', ''))
                if end_dt < now:
                    print(f"   ⚠️  End date in PAST: {allowance['end_datetime']}")
                else:
                    print(f"   End date: {allowance['end_datetime']}")
            else:
                print(f"   End date: None (runs forever)")

            if await create_allowance(client, config['base_url'], api_key, allowance):
                success_count += 1

            # Small delay between requests
            await asyncio.sleep(0.5)

    print(f"\n📊 Summary:")
    print(f"   ✅ Successfully created: {success_count}/{len(test_allowances)}")
    print(f"   ❌ Failed: {len(test_allowances) - success_count}/{len(test_allowances)}")

    if success_count == len(test_allowances):
        print("\n🎉 All test allowances created successfully!")
        return 0
    else:
        print("\n⚠️  Some allowances failed to create")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)