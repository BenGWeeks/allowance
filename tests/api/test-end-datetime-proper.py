#!/usr/bin/env python3
"""Test if end_datetime is being properly stored in the API."""

import asyncio
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from get_api_key import get_admin_api_key


async def test_end_datetime():
    """Test if end_datetime is properly stored."""
    print("🧪 Testing end_datetime storage")
    print("=" * 60)

    # Load config from .env.local
    env_path = Path(__file__).parent.parent.parent / ".env.local"
    if not env_path.exists():
        print(f"❌ .env.local not found at {env_path}")
        return False

    config = {}
    with open(env_path) as f:
        for line in f:
            if "=" in line and not line.startswith("#"):
                key, value = line.strip().split("=", 1)
                if key == "TEST_LNBITS_URL":
                    config["base_url"] = value

    # Override with local dev instance for testing
    base_url = "http://localhost:5001"

    # Get admin API key
    print("1️⃣ Getting admin API key...")
    admin_key = await get_admin_api_key()
    if not admin_key:
        print("❌ Failed to get admin API key")
        return False
    print(f"✓ Got admin key: {admin_key[:8]}...")

    async with httpx.AsyncClient() as client:
        # Create test allowance with end_datetime
        now = datetime.now(timezone.utc)
        end_time = now + timedelta(hours=1)

        test_data = {
            "name": "Test End DateTime Storage",
            "lightning_address": "test@localhost",
            "amount": 10,
            "currency": "sats",
            "frequency_type": "daily",
            "memo": "Testing end_datetime field",
            "active": True,
            "start_datetime": now.isoformat(),
            "end_datetime": end_time.isoformat(),
        }

        print("\n2️⃣ Creating allowance with end_datetime...")
        print(f"   Sending end_datetime: {test_data['end_datetime']}")

        headers = {"X-Api-Key": admin_key}
        create_response = await client.post(
            f"{base_url}/allowance/api/v1/allowance", json=test_data, headers=headers
        )

        if create_response.status_code != 201:
            print(f"❌ Failed to create allowance: {create_response.status_code}")
            print(f"   Response: {create_response.text}")
            return False

        created = create_response.json()
        allowance_id = created.get("id")
        print(f"✓ Created allowance ID: {allowance_id}")
        print(f"   Response end_datetime: {created.get('end_datetime')}")

        # Get the allowance to verify end_datetime was stored
        print("\n3️⃣ Retrieving allowance to verify storage...")
        get_response = await client.get(
            f"{base_url}/allowance/api/v1/allowance/{allowance_id}", headers=headers
        )

        if get_response.status_code != 200:
            print(f"❌ Failed to retrieve: {get_response.status_code}")
            return False

        retrieved = get_response.json()
        print(f"   Retrieved end_datetime: {retrieved.get('end_datetime')}")

        # Clean up
        print("\n4️⃣ Cleaning up test allowance...")
        delete_response = await client.delete(
            f"{base_url}/allowance/api/v1/allowance/{allowance_id}", headers=headers
        )
        if delete_response.status_code == 200:
            print("✓ Deleted test allowance")

        # Check results
        print("\n" + "=" * 60)
        if retrieved.get("end_datetime"):
            print("✅ SUCCESS: end_datetime is being stored correctly!")
            return True
        else:
            print("❌ FAILURE: end_datetime is NOT being stored!")
            print("\nFull retrieved data:")
            for key, value in retrieved.items():
                print(f"  {key}: {value}")
            return False


if __name__ == "__main__":
    success = asyncio.run(test_end_datetime())
    sys.exit(0 if success else 1)
