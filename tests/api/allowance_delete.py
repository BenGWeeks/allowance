"""
API test for DELETE /api/v1/allowance/{id} - Delete allowance endpoint
"""

import httpx
import asyncio


async def test_delete_allowance():
    """Test deleting an allowance via API - proper test with count verification"""
    base_url = "http://localhost:5001"

    try:
        # Get admin API key dynamically
        import sys
        import os
        sys.path.append(os.path.dirname(os.path.dirname(__file__)))
        from get_api_key import get_admin_api_key
        from datetime import datetime, timedelta
        
        admin_key = await get_admin_api_key()
        if not admin_key:
            print("❌ Failed to get admin API key")
            return False

        async with httpx.AsyncClient() as client:
            
            # Step 1: Count allowances before
            response = await client.get(
                f"{base_url}/allowance/api/v1/allowance",
                headers={"X-Api-Key": admin_key}
            )
            
            if response.status_code != 200:
                print(f"❌ Failed to get allowances: {response.status_code}")
                return False
                
            initial_count = len(response.json())
            print(f"📊 Initial allowance count: {initial_count}")
            
            # Step 2: Create a test allowance to delete
            create_data = {
                "name": "TEST_DELETE_ALLOWANCE",
                "lightning_address": "test@example.com",
                "amount": 1,
                "currency": "sats",
                "frequency_type": "weekly",
                "start_date": datetime.utcnow().isoformat(),
                "next_payment_date": (datetime.utcnow() + timedelta(days=7)).isoformat(),
                "active": True,
                "memo": "Test allowance for deletion"
            }
            
            create_response = await client.post(
                f"{base_url}/allowance/api/v1/allowance",
                json=create_data,
                headers={"X-Api-Key": admin_key}
            )
            
            if create_response.status_code != 201:
                print(f"❌ Failed to create test allowance: {create_response.status_code}")
                return False
                
            created_allowance = create_response.json()
            test_id = created_allowance["id"]
            print(f"✅ Created test allowance: {test_id}")
            
            # Step 3: Delete the test allowance
            delete_response = await client.delete(
                f"{base_url}/allowance/api/v1/allowance/{test_id}",
                headers={"X-Api-Key": admin_key}
            )

            print(f"Delete allowance API response: {delete_response.status_code}")

            if delete_response.status_code != 200:
                print(f"❌ Failed to delete allowance: HTTP {delete_response.status_code}")
                print(f"   Response: {delete_response.text}")
                return False
                
            print(f"✅ Deleted allowance: {test_id}")
            
            # Step 4: Verify count decreased by 1
            final_response = await client.get(
                f"{base_url}/allowance/api/v1/allowance",
                headers={"X-Api-Key": admin_key}
            )
            
            if final_response.status_code != 200:
                print(f"❌ Failed to get final allowances: {final_response.status_code}")
                return False
                
            final_count = len(final_response.json())
            print(f"📊 Final allowance count: {final_count}")
            
            if final_count == initial_count:
                print(f"✅ Count verification passed: {initial_count} -> {final_count}")
                return True
            else:
                print(f"❌ Count verification failed: expected {initial_count}, got {final_count}")
                return False

    except Exception as e:
        print(f"❌ API test error: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(test_delete_allowance())
    exit(0 if success else 1)
