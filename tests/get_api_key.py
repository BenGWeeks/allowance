#!/usr/bin/env python3
"""
Helper script to get API key from LNBits using username/password authentication.
This avoids hardcoding API keys in tests.
"""

import httpx
import asyncio

LNBITS_URL = "http://localhost:5001"
USERNAME = "ben.weeks"
PASSWORD = "zUYmy&05&uZ$3kmf*^T8"

async def get_admin_api_key():
    """Get the admin API key using username/password authentication"""
    try:
        async with httpx.AsyncClient() as client:
            # Step 1: Login to get access token
            login_response = await client.post(
                f"{LNBITS_URL}/api/v1/auth",
                json={"username": USERNAME, "password": PASSWORD}
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
                headers={"Authorization": f"Bearer {access_token}"}
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

def get_admin_api_key_sync():
    """Synchronous wrapper for getting admin API key"""
    return asyncio.run(get_admin_api_key())

if __name__ == "__main__":
    key = get_admin_api_key_sync()
    if key:
        print(f"\nAdmin API Key: {key}")
    else:
        print("Failed to get API key")
        exit(1)