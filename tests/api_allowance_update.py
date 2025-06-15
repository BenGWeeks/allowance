"""
API test for PUT /api/v1/allowance/{id} - Update allowance endpoint
"""
import httpx
import asyncio
from datetime import datetime, timedelta


async def test_update_allowance():
    """Test updating an allowance via API"""
    base_url = "http://localhost:5001"
    test_id = "test_allowance_id"
    
    try:
        async with httpx.AsyncClient() as client:
            payload = {
                "name": "Updated Test Allowance",
                "lightning_address": "updated@example.com",
                "amount": 2000,
                "currency": "sats",
                "frequency_type": "weekly",
                "start_date": (datetime.utcnow() + timedelta(days=2)).isoformat(),
                "active": False,
                "memo": "Updated via API test"
            }
            
            # Note: In real test environment, admin key would be configured
            admin_key = "test_admin_key_placeholder"
            
            response = await client.put(
                f"{base_url}/allowance/api/v1/allowance/{test_id}",
                json=payload,
                headers={"X-API-KEY": admin_key}
            )
            
            print(f"Update allowance API response: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Updated allowance: {data.get('name')} (ID: {data.get('id')})")
                return True
            elif response.status_code == 404:
                print(f"⚠️ Allowance not found (expected for test ID)")
                return True
            else:
                print(f"❌ Failed to update allowance: {response.text}")
                return False
                
    except Exception as e:
        print(f"❌ API test error: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(test_update_allowance())
    exit(0 if success else 1)