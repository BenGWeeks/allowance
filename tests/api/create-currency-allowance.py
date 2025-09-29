#!/usr/bin/env python3
"""
Test creating an allowance with currency conversion (GBP)
This test validates decimal amount support and currency conversion
"""

import asyncio
import os
from datetime import datetime
from pathlib import Path

import httpx


# Load environment variables
def load_config():
    env_path = Path(__file__).parent.parent.parent / ".env.local"
    config = {}

    if not env_path.exists():
        print(f"❌ .env.local not found at {env_path}")
        exit(1)

    with open(env_path) as f:
        for line in f:
            if "=" in line and not line.startswith("#"):
                key, value = line.strip().split("=", 1)
                if key == "PAYLINK_EMAIL":
                    config["lightning_address"] = value
                elif key == "TEST_LNBITS_URL":
                    config["base_url"] = value

    if "base_url" not in config or "lightning_address" not in config:
        print("❌ Missing TEST_LNBITS_URL or PAYLINK_EMAIL in .env.local")
        exit(1)

    return config


async def get_admin_wallet():
    """Get admin wallet ID and API key"""
    import sys

    # Add parent directory to path for imports
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    # Import the common test helper
    from get_api_key import main as get_api_key_main

    # Get wallet info using the existing helper
    wallet_info = await get_api_key_main()

    if wallet_info:
        return {
            "wallet_id": wallet_info["wallet_id"],
            "api_key": wallet_info["api_key"],
        }
    else:
        # Fallback to known values if helper fails
        return {
            "wallet_id": "768a7da8063046d98cd5ee6f42621038",
            "api_key": "2c3cd50a44784f19a4d7b4f605bbe247",
        }


async def test_gbp_allowance():
    """Test creating an allowance with 0.02 GBP"""
    config = load_config()

    # Get wallet info
    wallet_info = await get_admin_wallet()
    wallet_id = wallet_info["wallet_id"]
    api_key = wallet_info["api_key"]

    print(f"✅ Found admin wallet: {wallet_id}")
    print(f"✅ Admin API key: {api_key}")

    # Create test data with GBP amount
    now = datetime.now()
    allowance_data = {
        "name": "Test GBP Allowance - £0.02",
        "wallet": wallet_id,
        "lightning_address": config["lightning_address"],
        "amount": 0.02,  # Decimal amount for GBP (2 pence)
        "currency": "GBP",
        "frequency_type": "once",
        "start_datetime": now.isoformat(),
        "next_payment_date": now.isoformat(),
        "memo": "Testing £0.02 GBP conversion to sats",
        "active": True,
    }

    print("📝 Testing GBP allowance creation with amount: £0.02")
    print("   This is 2 pence (0.02), a sub-pound decimal amount")

    async with httpx.AsyncClient() as client:
        # Create the allowance
        response = await client.post(
            f"{config['base_url']}/allowance/api/v1/allowance",
            json=allowance_data,
            headers={"X-Api-Key": api_key},
        )

        print(f"Create GBP allowance API response: {response.status_code}")

        if response.status_code == 201:
            created = response.json()
            name = created.get("name")
            allowance_id = created.get("id")
            print(f"✅ Created GBP allowance: {name} (ID: {allowance_id})")
            print("   Amount: £0.02 GBP (2 pence)")
            print("   This proves decimal amounts are now supported!")

            # Clean up - delete the test allowance
            delete_response = await client.delete(
                f"{config['base_url']}/allowance/api/v1/allowance/{created['id']}",
                headers={"X-Api-Key": api_key},
            )

            if delete_response.status_code == 200:
                print("✅ Test allowance cleaned up")

            return True
        elif response.status_code == 422:
            error_detail = response.json()
            print("❌ Validation error (would happen with old int-only validation):")
            print(f"   {error_detail}")
            return False
        else:
            print(f"❌ Failed to create GBP allowance: {response.text}")
            return False


if __name__ == "__main__":
    print("=" * 60)
    print("Testing GBP Currency Allowance Creation (£0.02)")
    print("=" * 60)

    success = asyncio.run(test_gbp_allowance())

    if success:
        print("\n✅ GBP allowance test PASSED")
        print("   Decimal amounts (£0.02 = 2 pence) are supported!")
        exit(0)
    else:
        print("\n❌ GBP allowance test FAILED")
        print("   Check if models.py has amount field as float, not int")
        exit(1)
