#!/usr/bin/env python3
"""Simple test to check if end_datetime is being stored."""

from datetime import datetime, timedelta, timezone

import httpx

# Test with hardcoded admin key (from previous test runs)
ADMIN_KEY = "c0a1f21b1dc146a186f84f44f60b30a9"
BASE_URL = "http://localhost:5001"


def test():
    print("Testing end_datetime storage...")

    now = datetime.now(timezone.utc)
    end_time = now + timedelta(hours=1)

    test_data = {
        "name": "Test End DateTime Storage",
        "lightning_address": "test@localhost",
        "amount": 10,
        "currency": "sats",
        "frequency_type": "daily",
        "memo": "Testing end_datetime",
        "active": True,
        "start_datetime": now.isoformat(),
        "end_datetime": end_time.isoformat(),
    }

    print(f"Creating with end_datetime: {test_data['end_datetime']}")

    with httpx.Client(base_url=BASE_URL, timeout=30.0) as client:
        # Create allowance
        headers = {"X-Api-Key": ADMIN_KEY}
        response = client.post(
            "/allowance/api/v1/allowance", json=test_data, headers=headers
        )

        if response.status_code != 201:
            print(f"❌ Failed to create: {response.status_code} - {response.text}")
            return False

        created = response.json()
        allowance_id = created.get("id")
        print(f"Created ID: {allowance_id}")
        print(f"Response end_datetime: {created.get('end_datetime')}")

        # Retrieve to verify
        get_response = client.get(
            f"/allowance/api/v1/allowance/{allowance_id}", headers=headers
        )
        if get_response.status_code == 200:
            retrieved = get_response.json()
            print(f"Retrieved end_datetime: {retrieved.get('end_datetime')}")

            # Clean up
            client.delete(
                f"/allowance/api/v1/allowance/{allowance_id}", headers=headers
            )

            if retrieved.get("end_datetime"):
                print("✅ SUCCESS: end_datetime is stored!")
                return True
            else:
                print("❌ FAILURE: end_datetime is NOT stored!")
                print(f"Full data: {retrieved}")
                return False
        else:
            print(f"❌ Failed to retrieve: {get_response.status_code}")
            return False


if __name__ == "__main__":
    import sys

    success = test()
    sys.exit(0 if success else 1)
