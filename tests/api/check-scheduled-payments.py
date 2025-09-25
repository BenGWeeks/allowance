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
from datetime import datetime, timedelta, timezone
import httpx
from loguru import logger

# Configuration
import os
from pathlib import Path

# Load from .env.local
env_path = Path(__file__).parent.parent.parent / ".env.local"
config = {}
if env_path.exists():
    with open(env_path, "r") as f:
        for line in f:
            if "=" in line and not line.startswith("#"):
                key, value = line.strip().split("=", 1)
                config[key] = value

if "TEST_LNBITS_URL" not in config or "PAYLINK_EMAIL" not in config:
    print("❌ Missing TEST_LNBITS_URL or PAYLINK_EMAIL in .env.local")
    exit(1)

LNBITS_URL = config["TEST_LNBITS_URL"]
LIGHTNING_ADDRESS = config["PAYLINK_EMAIL"]
TEST_ALLOWANCE_NAME = (
    f"TEST_Minutely_{datetime.now().strftime('%H%M%S')}_{int(time.time())}"
)
AMOUNT_SATS = 1  # 1 sat to minimize cost
ADMIN_API_KEY = None  # Will be set from admin wallet


async def get_admin_wallet():
    """Get the default admin wallet ID and API key"""
    try:
        # Get admin API key dynamically
        import sys
        import os

        sys.path.append(os.path.dirname(os.path.dirname(__file__)))
        from get_api_key import main as get_api_key_main

        wallet_info = await get_api_key_main()
        if not wallet_info:
            logger.error("Failed to get wallet info")
            return None, None

        wallet_id = wallet_info.get("wallet_id", "768a7da8063046d98cd5ee6f42621038")
        admin_key = wallet_info.get("api_key")
        return wallet_id, admin_key

    except Exception as e:
        logger.error(f"Error getting admin wallet: {e}")
        return None, None


async def create_test_allowance(wallet_id: str, admin_key: str):
    """Create a test allowance via API"""
    try:
        now = datetime.now(timezone.utc)
        end_time = now + timedelta(
            minutes=5
        )  # Stop after 5 minutes to ensure 3+ payments

        allowance_data = {
            "name": TEST_ALLOWANCE_NAME,
            "wallet": wallet_id,
            "lightning_address": LIGHTNING_ADDRESS,
            "amount": AMOUNT_SATS,
            "currency": "sats",
            "start_datetime": now.isoformat(),
            "frequency_type": "minutely",
            "next_payment_date": now.isoformat(),  # Start immediately
            "memo": "Automated test payment - VoidWallet will cause failure",
            "active": True,
            "end_datetime": end_time.isoformat(),
        }

        headers = {"X-Api-Key": admin_key, "Content-Type": "application/json"}

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{LNBITS_URL}/allowance/api/v1/allowance",
                json=allowance_data,
                headers=headers,
                timeout=30.0,
            )

            if response.status_code == 201:
                allowance = response.json()
                logger.info(f"✅ Created test allowance: {allowance['id']}")
                return allowance["id"]
            else:
                logger.error(
                    f"❌ Failed to create allowance: {response.status_code} - {response.text}"
                )
                return None

    except Exception as e:
        logger.error(f"❌ Error creating test allowance: {e}")
        return None


async def monitor_payments(
    allowance_id: str, allowance_name: str, admin_key: str, duration_seconds: int = 360
):
    """Monitor for payment attempts over specified duration"""
    logger.info(
        f"📊 Monitoring allowance '{allowance_name}' (ID: {allowance_id}) for {duration_seconds} seconds..."
    )

    start_time = time.time()
    payment_attempts: list[dict] = []

    headers = {"X-Api-Key": admin_key}

    while time.time() - start_time < duration_seconds:
        try:
            async with httpx.AsyncClient() as client:
                # Check payments - look for our specific allowance name in memo/tag
                response = await client.get(
                    f"{LNBITS_URL}/api/v1/payments", headers=headers, timeout=10.0
                )

                if response.status_code == 200:
                    payments = response.json()

                    # Look for payments with our allowance name or ID
                    for payment in payments:
                        extra = payment.get("extra", {})
                        tag = extra.get("tag", "")
                        memo = payment.get("memo", "")

                        # Check multiple ways the payment might be tagged
                        is_our_payment = (
                            ("allowance" in tag.lower() and allowance_name in tag)
                            or (extra.get("allowance_id") == allowance_id)
                            or (extra.get("allowance_name") == allowance_name)
                            or (allowance_name in memo)
                            or (f"allowance: {allowance_name}" in tag)
                        )

                        if is_our_payment and payment.get("pending") == False:
                            payment_time = payment.get("time", 0)
                            if payment_time not in [
                                p["time"] for p in payment_attempts
                            ]:
                                payment_attempts.append(
                                    {
                                        "time": payment_time,
                                        "amount": payment.get("amount"),
                                        "status": "completed",
                                        "checking_id": payment.get("checking_id"),
                                        "memo": memo,
                                        "tag": tag,
                                    }
                                )
                                logger.info(
                                    f"💰 Payment detected for {allowance_name}: {len(payment_attempts)} total"
                                )
                                logger.debug(
                                    f"   Payment details: amount={payment.get('amount')}, memo={memo}, tag={tag}"
                                )

        except Exception as e:
            logger.warning(f"⚠️ Error checking payments: {e}")

        # Wait 10 seconds before next check
        await asyncio.sleep(10)

        elapsed_minutes = (time.time() - start_time) / 60
        logger.info(
            f"⏳ Monitoring... {elapsed_minutes:.1f} minutes elapsed, {len(payment_attempts)} payments detected for {allowance_name}"
        )

    return payment_attempts


async def delete_test_allowance(allowance_id: str, admin_key: str):
    """Clean up by deleting the test allowance"""
    try:
        headers = {"X-Api-Key": admin_key}

        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"{LNBITS_URL}/allowance/api/v1/allowance/{allowance_id}",
                headers=headers,
                timeout=30.0,
            )

            if response.status_code == 200:
                logger.info(f"✅ Cleaned up test allowance: {allowance_id}")
                return True
            else:
                logger.error(
                    f"❌ Failed to delete allowance: {response.status_code} - {response.text}"
                )
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
    logger.info(f"⏰ Duration: 5 minutes (expecting 3-5 payment attempts)")

    # Step 3: Monitor for payments (6 minutes to ensure we capture at least 3)
    logger.info("📋 Step 3: Monitoring for payment attempts...")
    payment_attempts = await monitor_payments(
        allowance_id, TEST_ALLOWANCE_NAME, admin_key, 360
    )

    # Step 4: Validate results
    logger.info("📋 Step 4: Validating results...")
    expected_payments = 3  # At least 3 payments in 5 minutes
    actual_payments = len(payment_attempts)

    logger.info(f"📊 Test Results for {TEST_ALLOWANCE_NAME}:")
    logger.info(f"   Allowance ID: {allowance_id}")
    logger.info(f"   Expected payments: {expected_payments}")
    logger.info(f"   Actual payments: {actual_payments}")

    if payment_attempts:
        logger.info("   Payment details:")
        for i, payment in enumerate(payment_attempts, 1):
            logger.info(
                f"     Payment {i}: {payment.get('amount', 0)} sats - {payment.get('status', 'unknown')}"
            )

    if actual_payments >= expected_payments:
        logger.info(
            f"✅ SUCCESS: {actual_payments} scheduled payments executed successfully!"
        )
        test_passed = True
    else:
        logger.error(
            f"❌ FAILURE: Expected at least {expected_payments} payment attempts, got {actual_payments}"
        )
        test_passed = False

    # Step 5: Cleanup
    logger.info("📋 Step 5: Cleaning up test allowance...")
    cleanup_success = await delete_test_allowance(allowance_id, admin_key)

    if cleanup_success:
        logger.info("✅ Cleanup completed successfully")
    else:
        logger.warning("⚠️ Cleanup failed - manual deletion may be required")

    # Final result
    if test_passed:
        logger.info("🎉 SCHEDULED PAYMENTS TEST PASSED!")
        return True
    else:
        logger.error("💥 SCHEDULED PAYMENTS TEST FAILED!")
        return False


if __name__ == "__main__":
    print("🧪 Scheduled payments integration test")
    print("=" * 60)

    # Actually run the test
    result = asyncio.run(main())
    exit(0 if result else 1)
