#!/usr/bin/env python3
"""
Test script for scheduled payments functionality.

This script:
1. Creates a new scheduled payment from the default admin wallet
2. Sends it to muddledsmell08@walletofsatoshi.com
3. Gives it a clear dev testing name
4. Starts immediately and stops after 2 minutes  
5. Validates that 2 payments were attempted
6. Cleans up by deleting the allowance

Usage: python test_scheduled_payments.py
"""

import asyncio
import time
from datetime import datetime, timedelta
import httpx
from loguru import logger

# Configuration
LNBITS_URL = "http://localhost:5001"
LIGHTNING_ADDRESS = "muddledsmell08@walletofsatoshi.com"
TEST_ALLOWANCE_NAME = f"DEV_TEST_Scheduled_Payment_{int(time.time())}"
AMOUNT_SATS = 1  # 1 sat to minimize cost
ADMIN_API_KEY = None  # Will be set from admin wallet

async def get_admin_wallet():
    """Get the default admin wallet ID and API key"""
    try:
        # First, get list of wallets to find admin wallet
        async with httpx.AsyncClient() as client:
            # This endpoint typically requires no auth for local admin access
            response = await client.get(f"{LNBITS_URL}/api/v1/wallets")
            
            if response.status_code == 200:
                wallets = response.json()
                if wallets:
                    # Use first wallet as admin wallet
                    admin_wallet = wallets[0]
                    return admin_wallet["id"], admin_wallet["adminkey"]
            
            logger.error(f"Failed to get admin wallet: {response.status_code}")
            return None, None
            
    except Exception as e:
        logger.error(f"Error getting admin wallet: {e}")
        return None, None

async def create_test_allowance(wallet_id: str, admin_key: str):
    """Create a test allowance via API"""
    try:
        now = datetime.utcnow()
        end_time = now + timedelta(minutes=2)  # Stop after 2 minutes
        
        allowance_data = {
            "name": TEST_ALLOWANCE_NAME,
            "wallet": wallet_id,
            "lightning_address": LIGHTNING_ADDRESS,
            "amount": AMOUNT_SATS,
            "currency": "sats",
            "start_date": now.isoformat(),
            "frequency_type": "minutely",
            "next_payment_date": now.isoformat(),  # Start immediately
            "memo": "Automated test payment - VoidWallet will cause failure",
            "active": True,
            "end_date": end_time.isoformat()
        }
        
        headers = {
            "X-Api-Key": admin_key,
            "Content-Type": "application/json"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{LNBITS_URL}/allowance/api/v1/allowances",
                json=allowance_data,
                headers=headers,
                timeout=30.0
            )
            
            if response.status_code == 201:
                allowance = response.json()
                logger.info(f"✅ Created test allowance: {allowance['id']}")
                return allowance["id"]
            else:
                logger.error(f"❌ Failed to create allowance: {response.status_code} - {response.text}")
                return None
                
    except Exception as e:
        logger.error(f"❌ Error creating test allowance: {e}")
        return None

async def monitor_payments(allowance_id: str, admin_key: str, duration_seconds: int = 150):
    """Monitor for payment attempts over specified duration"""
    logger.info(f"📊 Monitoring for {duration_seconds} seconds...")
    
    start_time = time.time()
    payment_attempts = []
    
    headers = {"X-Api-Key": admin_key}
    
    while time.time() - start_time < duration_seconds:
        try:
            async with httpx.AsyncClient() as client:
                # Check payments with allowance tag
                response = await client.get(
                    f"{LNBITS_URL}/api/v1/payments",
                    headers=headers,
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    payments = response.json()
                    
                    # Look for payments with allowance tag and our allowance ID
                    for payment in payments:
                        extra = payment.get("extra", {})
                        if (extra.get("tag") == "allowance" and 
                            extra.get("allowance_id") == allowance_id):
                            
                            payment_time = payment.get("time", 0)
                            if payment_time not in [p["time"] for p in payment_attempts]:
                                payment_attempts.append({
                                    "time": payment_time,
                                    "amount": payment.get("amount"),
                                    "status": "attempted",
                                    "checking_id": payment.get("checking_id")
                                })
                                logger.info(f"💰 Payment attempt detected: {len(payment_attempts)} total")
        
        except Exception as e:
            logger.warning(f"⚠️ Error checking payments: {e}")
        
        # Wait 10 seconds before next check  
        await asyncio.sleep(10)
        
        elapsed_minutes = (time.time() - start_time) / 60
        logger.info(f"⏳ Monitoring... {elapsed_minutes:.1f} minutes elapsed, {len(payment_attempts)} payments detected")
    
    return payment_attempts

async def delete_test_allowance(allowance_id: str, admin_key: str):
    """Clean up by deleting the test allowance"""
    try:
        headers = {"X-Api-Key": admin_key}
        
        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"{LNBITS_URL}/allowance/api/v1/allowances/{allowance_id}",
                headers=headers,
                timeout=30.0
            )
            
            if response.status_code == 200:
                logger.info(f"✅ Cleaned up test allowance: {allowance_id}")
                return True
            else:
                logger.error(f"❌ Failed to delete allowance: {response.status_code} - {response.text}")
                return False
                
    except Exception as e:
        logger.error(f"❌ Error deleting test allowance: {e}")
        return False

async def main():
    """Main test execution"""
    logger.info("🚀 Starting scheduled payments test...")
    
    # Step 1: Get admin wallet
    logger.info("📋 Step 1: Getting admin wallet...")
    wallet_id, admin_key = await get_admin_wallet()
    
    if not wallet_id or not admin_key:
        logger.error("❌ Failed to get admin wallet credentials")
        return False
    
    logger.info(f"✅ Using admin wallet: {wallet_id}")
    
    # Step 2: Create test allowance
    logger.info("📋 Step 2: Creating test allowance...")
    allowance_id = await create_test_allowance(wallet_id, admin_key)
    
    if not allowance_id:
        logger.error("❌ Failed to create test allowance")
        return False
    
    logger.info(f"✅ Created allowance: {allowance_id}")
    logger.info(f"📧 Target: {LIGHTNING_ADDRESS}")
    logger.info(f"💰 Amount: {AMOUNT_SATS} sats every minute")
    logger.info(f"⏰ Duration: 2 minutes (expecting 2 payment attempts)")
    
    # Step 3: Monitor for payments (2.5 minutes to be safe)
    logger.info("📋 Step 3: Monitoring for payment attempts...")
    payment_attempts = await monitor_payments(allowance_id, admin_key, 150)
    
    # Step 4: Validate results
    logger.info("📋 Step 4: Validating results...")
    expected_payments = 2
    actual_payments = len(payment_attempts)
    
    logger.info(f"📊 Test Results:")
    logger.info(f"   Expected payments: {expected_payments}")
    logger.info(f"   Actual payments: {actual_payments}")
    
    if actual_payments >= expected_payments:
        logger.info("✅ SUCCESS: Scheduled payments are working correctly!")
        test_passed = True
    else:
        logger.error("❌ FAILURE: Expected at least 2 payment attempts")
        test_passed = False
    
    # Step 5: Cleanup (COMMENTED OUT FOR DEBUGGING)
    logger.info("📋 Step 5: Skipping cleanup to preserve allowance for inspection...")
    logger.info(f"💡 Allowance {allowance_id} left in system for manual inspection")
    # cleanup_success = await delete_test_allowance(allowance_id, admin_key)
    # 
    # if cleanup_success:
    #     logger.info("✅ Cleanup completed successfully")
    # else:
    #     logger.warning("⚠️ Cleanup failed - manual deletion may be required")
    
    # Final result
    if test_passed:
        logger.info("🎉 SCHEDULED PAYMENTS TEST PASSED!")
        return True
    else:
        logger.error("💥 SCHEDULED PAYMENTS TEST FAILED!")
        return False

if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("❌ Test interrupted by user")
        exit(1)
    except Exception as e:
        logger.error(f"❌ Test failed with exception: {e}")
        exit(1)