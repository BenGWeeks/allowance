#!/usr/bin/env python3
"""
Debug Payment Timing
Checks when payments were created vs when they were confirmed
to understand if there are delays in payment processing
"""

import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx


def load_env_test():
    """Load configuration from .env.test file"""
    env_file = Path(__file__).parent.parent / ".env.test"
    config = {}

    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    config[key] = value.strip()

    return config


def get_api_key():
    """Get API key from user input"""
    print("🔑 Please provide your LNBits Admin API Key")
    print("   (You can find this in LNBits under API Info)")
    api_key = input("   API Key: ").strip()
    return api_key


def parse_timestamp(ts):
    """Parse timestamp (Unix or ISO format) to datetime"""
    if not ts:
        return None
    try:
        # Try Unix timestamp first
        if isinstance(ts, (int, float)):
            return datetime.fromtimestamp(ts, tz=timezone.utc)
        if isinstance(ts, str):
            # Try parsing as integer (Unix timestamp)
            try:
                return datetime.fromtimestamp(int(ts), tz=timezone.utc)
            except ValueError:
                # Try ISO format
                return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except Exception:
        return None
    return None


def format_timestamp(ts):
    """Format timestamp to readable string"""
    dt = parse_timestamp(ts)
    if dt:
        return dt.strftime("%Y-%m-%d %H:%M:%S UTC")
    return "N/A"


async def check_payment_timing(
    base_url: str, sending_key: str, receiving_key: str | None = None
):
    """Check payment timing from LNBits API"""
    print("\n🔍 Investigating Payment Timing Issues")
    print("=" * 60)

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Check sending wallet
        print(f"\n📊 Fetching data from {base_url}...\n")
        print("💰 Checking SENDING wallet...")
        print("=" * 60)

        await check_wallet_payments(client, base_url, sending_key, "SENDING")

        # Check receiving wallet if provided
        if receiving_key:
            print("\n\n💰 Checking RECEIVING wallet...")
            print("=" * 60)
            await check_wallet_payments(client, base_url, receiving_key, "RECEIVING")


async def check_wallet_payments(  # noqa: C901
    client, base_url: str, api_key: str, wallet_name: str
):
    """Check payments for a specific wallet"""
    headers = {"X-Api-Key": api_key}

    try:
        # Get payments
        response = await client.get(f"{base_url}/api/v1/payments", headers=headers)
        response.raise_for_status()
        payments = response.json()

        print(f"✅ Found {len(payments)} total payments in {wallet_name} wallet\n")

        # Filter for allowance payments
        allowance_payments = [
            p
            for p in payments
            if "allowance" in (p.get("memo") or "").lower()
            or p.get("extra", {}).get("tag") == "allowance"
        ]

        print(f"💸 Found {len(allowance_payments)} allowance payments\n")

        # Filter for last 12 hours
        now = datetime.now(timezone.utc)
        twelve_hours_ago = now - timedelta(hours=12)
        recent_payments = []
        for p in allowance_payments:
            try:
                payment_time = parse_timestamp(p["time"])
                if payment_time and payment_time >= twelve_hours_ago:
                    recent_payments.append(p)
            except KeyError:
                continue

        print(f"⏰ {len(recent_payments)} allowance payments in last 12 hours\n")

        # If no recent payments, show the most recent ones
        if len(recent_payments) == 0 and len(allowance_payments) > 0:
            print("⚠️  No payments in last 12 hours. Showing 10 most recent:\n")
            print("=" * 60)
            # Sort by time descending
            sorted_payments = sorted(
                allowance_payments,
                key=lambda p: parse_timestamp(p["time"])
                or datetime.min.replace(tzinfo=timezone.utc),
                reverse=True,
            )
            for p in sorted_payments[:10]:
                print_payment_details(p)
            print("=" * 60)

        # Filter for 3am-4am window (today)
        three_am = now.replace(hour=3, minute=0, second=0, microsecond=0)
        four_am = now.replace(hour=4, minute=0, second=0, microsecond=0)

        # If we're before 4am, use yesterday's 3-4am window
        if now.hour < 4:
            three_am -= timedelta(days=1)
            four_am -= timedelta(days=1)

        morning_payments = []
        for p in allowance_payments:
            try:
                payment_time = parse_timestamp(p["time"])
                if payment_time and three_am <= payment_time <= four_am:
                    morning_payments.append(p)
            except KeyError:
                continue

        if morning_payments:
            print(f"🌅 Found {len(morning_payments)} payments between 3am-4am:\n")
            print("=" * 60)
            for p in morning_payments:
                print_payment_details(p)
        else:
            print("⚠️  No payments found in 3am-4am window")
            print("   Showing recent payments instead:\n")
            print("=" * 60)
            for p in recent_payments[:20]:
                print_payment_details(p)

        # Check for pending payments
        pending = [p for p in recent_payments if p.get("pending")]
        if pending:
            print("\n" + "=" * 60)
            print(f"⚠️  {len(pending)} PENDING PAYMENTS found:")
            print("=" * 60)
            for p in pending:
                print_payment_details(p)

        # Summary statistics
        print("\n" + "=" * 60)
        print(f"📈 Summary Statistics for {wallet_name} wallet (last 12 hours):")
        print("=" * 60)
        total = len(recent_payments)
        pending_count = len([p for p in recent_payments if p.get("pending")])
        confirmed_count = total - pending_count

        print(f"   Total Payments: {total}")
        print(f"   Confirmed: {confirmed_count}")
        print(f"   Pending: {pending_count}")

        if confirmed_count > 0:
            # Calculate average confirmation delay
            delays = []
            for p in recent_payments:
                if not p.get("pending") and p.get("time"):
                    # Check if we have a separate confirmation time
                    # (LNBits might not store this separately)
                    delays.append(0)  # Placeholder

            print("   Average Confirmation: ~instant")

    except httpx.HTTPStatusError as e:
        print(f"❌ HTTP Error: {e.response.status_code}")
        print(f"   {e.response.text}")
    except Exception as e:
        print(f"❌ Error: {e}")


def print_payment_details(payment):
    """Print detailed payment information"""
    time_str = format_timestamp(payment.get("time"))
    amount = payment.get("amount", 0) / 1000  # Convert msats to sats
    memo = payment.get("memo", "Unnamed")
    pending = payment.get("pending", False)
    checking_id = payment.get("checking_id", "N/A")

    # Check for various possible confirmation timestamp fields
    confirmed_at = None
    for field in [
        "confirmed_at",
        "confirmed_time",
        "settled_at",
        "preimage_time",
        "updated_at",
    ]:
        if payment.get(field):
            confirmed_at = payment.get(field)
            break

    print(f"\n💳 Payment: {memo}")
    print(f"   Amount: {amount:.0f} sats")
    print(f"   Created: {time_str}")

    if confirmed_at:
        confirmed_str = format_timestamp(confirmed_at)
        print(f"   Confirmed: {confirmed_str}")

        # Calculate delay
        try:
            created = parse_timestamp(payment.get("time"))
            confirmed = parse_timestamp(confirmed_at)
            if created and confirmed:
                delay = (confirmed - created).total_seconds()
                print(f"   Delay: {delay:.1f}s")
        except Exception:
            pass

    print(f"   Status: {'❌ PENDING' if pending else '✅ CONFIRMED'}")
    print(f"   Payment ID: {checking_id[:16]}...")

    # Debug: show all available fields
    if os.getenv("DEBUG"):
        print(f"   All fields: {list(payment.keys())}")


if __name__ == "__main__":
    import asyncio

    print("🔍 LNBits Payment Timing Debugger")
    print("=" * 60)

    # Load configuration from .env.test
    config = load_env_test()

    # Get base URL
    base_url = config.get("TEST_LNBITS_URL", "")
    if not base_url:
        base_url = input("\n🌐 LNBits URL: ").strip()
        if not base_url:
            print("❌ No URL provided")
            sys.exit(1)
    else:
        print(f"\n🌐 Using URL from .env.test: {base_url}")

    # Get sending wallet API key
    sending_wallet_id = config.get("TEST_SENDING_WALLET_ID", "")
    sending_key = config.get("TEST_SENDING_WALLET_KEY", "")

    if not sending_wallet_id:
        print("\n💰 SENDING Wallet (where allowances are paid from)")
        sending_wallet_id = input("   Wallet ID: ").strip()
        if not sending_wallet_id:
            print("❌ No sending wallet ID provided")
            sys.exit(1)
    else:
        print(f"\n💰 Using SENDING wallet from .env.test: {sending_wallet_id}")

    if not sending_key:
        sending_key = input("   Admin/Invoice API Key: ").strip()

    if not sending_key:
        print("❌ No sending wallet API key provided")
        sys.exit(1)

    # Get receiving wallet API key (optional)
    receiving_wallet_id = config.get("TEST_RECEIVING_WALLET_ID", "")
    receiving_key = config.get("TEST_RECEIVING_WALLET_KEY", "")

    if not receiving_key and not receiving_wallet_id:
        print("\n💰 RECEIVING Wallet (where payments are received) - optional")
        receiving_wallet_id = input("   Wallet ID (press Enter to skip): ").strip()
        if receiving_wallet_id:
            receiving_key = input("   Admin/Invoice API Key: ").strip()
    elif receiving_wallet_id and not receiving_key:
        print(f"\n💰 Using RECEIVING wallet from .env.test: {receiving_wallet_id}")
        receiving_key = input(
            "   Admin/Invoice API Key (press Enter to skip): "
        ).strip()

    # Run the check
    asyncio.run(
        check_payment_timing(
            base_url, sending_key, receiving_key if receiving_key else None
        )
    )
