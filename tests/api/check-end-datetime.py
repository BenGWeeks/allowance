#!/usr/bin/env python3
"""Test if end_datetime is being properly stored in the API."""

import os
import random
import sys
from datetime import datetime, timedelta, timezone

import httpx

# Read .env.local file manually
env_file = ".env.local"
if os.path.exists(env_file):
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                key, value = line.split("=", 1)
                os.environ[key] = value

BASE_URL = os.getenv("TEST_LNBITS_URL")
USERNAME = os.getenv("LNBITS_ADMIN_USERNAME")
PASSWORD = os.getenv("LNBITS_ADMIN_PASSWORD")

if not USERNAME or not PASSWORD:
    print("❌ Missing LNBITS_ADMIN_USERNAME or LNBITS_ADMIN_PASSWORD in .env.local")
    sys.exit(1)


def test_end_datetime():
    """Test if end_datetime is properly stored."""
    print("🧪 Testing end_datetime storage")
    print("=" * 60)

    with httpx.Client(base_url=BASE_URL, timeout=30.0) as client:
        # Login
        print(f"1️⃣ Logging in as {USERNAME}...")
        try:
            login_response = client.post(
                "/api/v1/auth", json={"username": USERNAME, "password": PASSWORD}
            )
            login_response.raise_for_status()
            login_data = login_response.json()
            access_token = login_data.get("access_token")
            if not access_token:
                print(f"❌ No access token in response: {login_data}")
                return False
        except Exception as e:
            print(f"❌ Login failed: {e}")
            return False

        headers = {"Authorization": f"Bearer {access_token}"}

        # Get wallet info
        print("2️⃣ Getting wallet info...")
        wallet_response = client.get("/allowance/api/v1/wallet-info", headers=headers)
        wallet_response.raise_for_status()
        wallet_data = wallet_response.json()
        admin_key = wallet_data.get("adminkey")

        # Create test allowance with end_datetime
        now = datetime.now(timezone.utc)
        end_time = now + timedelta(hours=1)

        test_data = {
            "name": "Test End DateTime",
            "lightning_address": "test@localhost",
            "amount": random.randint(1, 99),  # Random amount between 1-99 sats
            "currency": "sats",
            "frequency_type": "daily",
            "memo": "Testing end_datetime",
            "active": True,
            "start_datetime": now.isoformat(),
            "end_datetime": end_time.isoformat(),
        }

        print(f"3️⃣ Creating allowance with end_datetime: {end_time.isoformat()}")

        headers = {"X-Api-Key": admin_key}
        create_response = client.post(
            "/allowance/api/v1/allowance", json=test_data, headers=headers
        )

        if create_response.status_code != 201:
            print(f"❌ Failed to create: {create_response.text}")
            return False

        created = create_response.json()
        allowance_id = created.get("id")

        print(f"✓ Created allowance ID: {allowance_id}")
        print(f"  Sent end_datetime: {test_data['end_datetime']}")
        print(f"  Received end_datetime: {created.get('end_datetime')}")

        # Get the allowance to verify end_datetime was stored
        print("4️⃣ Retrieving allowance to verify end_datetime...")
        get_response = client.get(
            f"/allowance/api/v1/allowance/{allowance_id}", headers=headers
        )
        get_response.raise_for_status()
        retrieved = get_response.json()

        print(f"  Retrieved end_datetime: {retrieved.get('end_datetime')}")

        # Clean up
        print("5️⃣ Cleaning up test allowance...")
        client.delete(f"/allowance/api/v1/allowance/{allowance_id}", headers=headers)

        # Check if end_datetime was stored
        if retrieved.get("end_datetime"):
            print("\n✅ SUCCESS: end_datetime is being stored correctly!")
            return True
        else:
            print("\n❌ FAILURE: end_datetime is NOT being stored!")
            print(f"Full retrieved data: {retrieved}")
            return False


if __name__ == "__main__":
    success = test_end_datetime()
    sys.exit(0 if success else 1)
