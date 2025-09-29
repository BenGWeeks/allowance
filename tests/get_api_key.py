#!/usr/bin/env python3
"""
Helper script to get API key from LNBits using username/password authentication.
This avoids hardcoding API keys in tests.
"""

import asyncio
from pathlib import Path

import httpx

# Load config from .env.local
env_path = Path(__file__).parent.parent / ".env.local"
config = {}

if not env_path.exists():
    print(f"❌ .env.local not found at {env_path}")
    exit(1)

with open(env_path) as f:
    for line in f:
        if "=" in line and not line.startswith("#"):
            key, value = line.strip().split("=", 1)
            config[key] = value

# Check required variables
required = ["TEST_LNBITS_URL", "LNBITS_ADMIN_USERNAME", "LNBITS_ADMIN_PASSWORD"]
missing = [k for k in required if k not in config]
if missing:
    print(f"❌ Missing required variables in .env.local: {', '.join(missing)}")
    exit(1)

LNBITS_URL = config["TEST_LNBITS_URL"]
USERNAME = config["LNBITS_ADMIN_USERNAME"]
PASSWORD = config["LNBITS_ADMIN_PASSWORD"]


async def get_admin_api_key():
    """Get the admin API key using username/password authentication"""
    try:
        async with httpx.AsyncClient() as client:
            # Step 1: Login to get access token
            login_response = await client.post(
                f"{LNBITS_URL}/api/v1/auth",
                json={"username": USERNAME, "password": PASSWORD},
            )

            if login_response.status_code != 200:
                print(f"❌ Login failed: {login_response.status_code}")
                return None

            auth_data = login_response.json()
            access_token = auth_data.get("access_token")

            if not access_token:
                print("❌ No access token received")
                return None

            # Step 2: Get wallets using the access token
            wallets_response = await client.get(
                f"{LNBITS_URL}/api/v1/wallets",
                headers={"Authorization": f"Bearer {access_token}"},
            )

            if wallets_response.status_code != 200:
                print(f"❌ Failed to get wallets: {wallets_response.status_code}")
                return None

            wallets = wallets_response.json()

            if not wallets:
                print("❌ No wallets found")
                return None

            # Return the admin key from the first wallet
            admin_wallet = wallets[0]
            admin_key = admin_wallet.get("adminkey")
            wallet_id = admin_wallet.get("id")

            print(f"✅ Found admin wallet: {wallet_id}")
            print(f"✅ Admin API key: {admin_key}")

            return admin_key

    except Exception as e:
        print(f"❌ Error getting API key: {e}")
        return None


async def main():
    """Main function that returns both wallet_id and api_key"""
    try:
        async with httpx.AsyncClient() as client:
            # Step 1: Login to get access token
            login_response = await client.post(
                f"{LNBITS_URL}/api/v1/auth",
                json={"username": USERNAME, "password": PASSWORD},
            )

            if login_response.status_code != 200:
                print(f"❌ Login failed: {login_response.status_code}")
                return None

            auth_data = login_response.json()
            access_token = auth_data.get("access_token")

            if not access_token:
                print("❌ No access token received")
                return None

            # Step 2: Get wallets using the access token
            wallets_response = await client.get(
                f"{LNBITS_URL}/api/v1/wallets",
                headers={"Authorization": f"Bearer {access_token}"},
            )

            if wallets_response.status_code != 200:
                print(f"❌ Failed to get wallets: {wallets_response.status_code}")
                return None

            wallets = wallets_response.json()

            if not wallets:
                print("❌ No wallets found")
                return None

            # Return the admin key and wallet ID from the first wallet
            admin_wallet = wallets[0]
            admin_key = admin_wallet.get("adminkey")
            wallet_id = admin_wallet.get("id")

            print(f"✅ Found admin wallet: {wallet_id}")
            print(f"✅ Admin API key: {admin_key}")

            return {"wallet_id": wallet_id, "api_key": admin_key}

    except Exception as e:
        print(f"❌ Error getting wallet info: {e}")
        return None


def get_admin_api_key_sync():
    """Synchronous wrapper for getting admin API key"""
    return asyncio.run(get_admin_api_key())


if __name__ == "__main__":
    wallet_info = asyncio.run(main())
    if wallet_info:
        print(f"\nAdmin API Key: {wallet_info['api_key']}")
        print(f"Wallet ID: {wallet_info['wallet_id']}")
    else:
        print("Failed to get wallet info")
        exit(1)
