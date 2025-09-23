#!/usr/bin/env python3
"""Test scheduled payments with currency conversion (GBP to sats)"""

import httpx
import asyncio
import json
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Load configuration
env_path = Path(__file__).parent.parent.parent / '.env.local'
config = {}
if env_path.exists():
    with open(env_path) as f:
        for line in f:
            if '=' in line and not line.startswith('#'):
                key, value = line.strip().split('=', 1)
                config[key] = value

BASE_URL = config.get('TEST_LNBITS_URL', 'http://localhost:5001')
USERNAME = config.get('LNBITS_ADMIN_USERNAME', 'admin')
PASSWORD = config.get('LNBITS_ADMIN_PASSWORD', 'password')
LIGHTNING_ADDRESS = config.get('PAYLINK_EMAIL', 'test@example.com')

async def get_api_key():
    """Get admin API key from LNbits"""
    async with httpx.AsyncClient() as client:
        # Login
        login_response = await client.post(
            f"{BASE_URL}/api/v1/auth",
            json={"username": USERNAME, "password": PASSWORD}
        )
        if login_response.status_code != 200:
            raise Exception(f"Login failed: {login_response.text}")

        auth_data = login_response.json()
        return auth_data.get('access_token') or auth_data.get('api_key')

async def test_gbp_scheduled_payment():
    """Test creating and executing a GBP scheduled payment"""

    api_key = await get_api_key()
    headers = {"X-Api-Key": api_key}

    async with httpx.AsyncClient() as client:
        # Create allowance with GBP
        allowance_data = {
            "name": f"GBP Test {datetime.now().strftime('%H%M%S')}",
            "wallet": "768a7da8063046d98cd5ee6f42621038",  # Your wallet ID
            "lightning_address": LIGHTNING_ADDRESS,
            "amount": 0.02,  # £0.02 GBP
            "currency": "GBP",
            "frequency_type": "minutely",
            "memo": "Testing GBP to sats conversion",
            "active": True,
            "start_datetime": datetime.now(timezone.utc).isoformat(),
            "next_payment_date": datetime.now(timezone.utc).isoformat()
        }

        print(f"📝 Creating GBP allowance: £{allowance_data['amount']} GBP")

        # Create the allowance
        create_response = await client.post(
            f"{BASE_URL}/allowance/api/v1/allowances",
            json=allowance_data,
            headers=headers
        )

        if create_response.status_code != 201:
            print(f"❌ Failed to create allowance: {create_response.text}")
            return False

        created = create_response.json()
        allowance_id = created['id']
        print(f"✅ Created allowance: {created['name']}")
        print(f"   ID: {allowance_id}")
        print(f"   Amount: £{allowance_data['amount']} GBP")

        # Get current exchange rate
        rate_response = await client.get(
            f"{BASE_URL}/allowance/api/v1/rate/GBP",
            headers=headers
        )

        if rate_response.status_code == 200:
            rate_data = rate_response.json()
            sats_amount = int(allowance_data['amount'] / rate_data['rate'])
            print(f"   Exchange rate: £1 = {1/rate_data['rate']:.0f} sats")
            print(f"   Will pay: {sats_amount} sats per minute")

        # Wait for scheduler to process
        print("⏳ Waiting 65 seconds for first scheduled payment...")
        await asyncio.sleep(65)

        # Check if payment was made by getting allowance details
        get_response = await client.get(
            f"{BASE_URL}/allowance/api/v1/allowances/{allowance_id}",
            headers=headers
        )

        if get_response.status_code == 200:
            updated = get_response.json()
            print(f"📊 Allowance status after 1 minute:")
            print(f"   Total paid: {updated.get('total', 0)} sats")
            print(f"   Next payment: {updated.get('next_payment_date', 'N/A')}")

        # Clean up - delete the test allowance
        delete_response = await client.delete(
            f"{BASE_URL}/allowance/api/v1/allowances/{allowance_id}",
            headers=headers
        )

        if delete_response.status_code in [200, 204]:
            print("✅ Test allowance deleted")

        return True

async def main():
    """Run the test"""
    print("🌍 Testing scheduled payments with GBP currency...")

    try:
        success = await test_gbp_scheduled_payment()
        if success:
            print("✅ GBP scheduled payment test completed successfully")
        else:
            print("❌ GBP scheduled payment test failed")
            exit(1)
    except Exception as e:
        print(f"❌ Test error: {e}")
        exit(1)

if __name__ == "__main__":
    asyncio.run(main())