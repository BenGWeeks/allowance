import asyncio
import httpx
from datetime import datetime, timedelta, timezone
from dateutil.relativedelta import relativedelta
from typing import List, Tuple, Dict, Any

from lnbits.core.services import pay_invoice
from loguru import logger
from lnurl import decode as lnurl_decode

from .crud import get_all_active_allowances, update_next_payment_date, deactivate_allowance
from .models import Allowance


async def resolve_lightning_address(
    lightning_address: str,
) -> Tuple[str, Dict[str, Any]]:
    """
    Convert Lightning address (user@domain.com) to LNURL-pay endpoint
    Returns tuple of (callback_url, lnurl_data)
    """
    if lightning_address.startswith("lnurl") or lightning_address.startswith("LNURL"):
        # Already an LNURL, decode it
        try:
            decoded_url = lnurl_decode(lightning_address)
            async with httpx.AsyncClient() as client:
                response = await client.get(decoded_url, timeout=10.0)
                response.raise_for_status()
                lnurl_data = response.json()
                return lnurl_data.get("callback"), lnurl_data
        except Exception as e:
            logger.error(f"Failed to decode LNURL: {e}")
            raise Exception(f"Invalid LNURL: {lightning_address}")

    if "@" not in lightning_address:
        raise Exception(f"Invalid Lightning address format: {lightning_address}")

    # Split the Lightning address
    user, domain = lightning_address.split("@", 1)

    # Construct the well-known URL
    well_known_url = f"https://{domain}/.well-known/lnurlp/{user}"

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(well_known_url, timeout=10.0)
            response.raise_for_status()

            lnurl_data = response.json()
            callback_url = lnurl_data.get("callback")

            if not callback_url:
                raise Exception("No callback URL found in LNURL-pay response")

            return callback_url, lnurl_data

    except httpx.HTTPError as e:
        logger.error(f"HTTP error resolving Lightning address {lightning_address}: {e}")
        raise Exception(f"Failed to resolve Lightning address: {lightning_address}")
    except Exception as e:
        logger.error(f"Error resolving Lightning address {lightning_address}: {e}")
        raise Exception(f"Failed to resolve Lightning address: {lightning_address}")


async def get_invoice_from_lnurl(
    callback_url: str, amount_msats: int, memo: str = ""
) -> str:
    """
    Get invoice from LNURL-pay callback URL
    Returns the payment request (invoice)
    """
    try:
        params: dict[str, int | str] = {
            "amount": amount_msats,  # Amount in millisatoshis
        }

        if memo:
            params["comment"] = memo

        async with httpx.AsyncClient() as client:
            response = await client.get(callback_url, params=params, timeout=10.0)
            response.raise_for_status()

            invoice_data = response.json()

            if invoice_data.get("status") == "ERROR":
                error_reason = invoice_data.get("reason", "Unknown error")
                raise Exception(f"LNURL-pay error: {error_reason}")

            payment_request = invoice_data.get("pr")
            if not payment_request:
                raise Exception("No payment request found in LNURL-pay response")

            return payment_request

    except httpx.HTTPError as e:
        logger.error(f"HTTP error getting invoice from LNURL: {e}")
        raise Exception(f"Failed to get invoice from LNURL endpoint")
    except Exception as e:
        logger.error(f"Error getting invoice from LNURL: {e}")
        raise Exception(f"Failed to get invoice from LNURL endpoint")


async def execute_lightning_address_payment(allowance: Allowance) -> bool:
    """
    Execute payment to Lightning address
    Returns True if successful, False otherwise
    """
    try:
        # Convert sats to millisatoshis
        amount_msats = allowance.amount * 1000

        # Step 1: Resolve Lightning address to LNURL-pay endpoint
        logger.info(f"🔍 Resolving Lightning address: {allowance.lightning_address}")
        callback_url, lnurl_data = await resolve_lightning_address(
            allowance.lightning_address
        )

        # Step 2: Validate amount limits and comment capability
        min_sendable = lnurl_data.get("minSendable", 1000)  # Default 1 sat minimum
        max_sendable = lnurl_data.get(
            "maxSendable", 100000000000
        )  # Default 100k sats max
        comment_allowed = lnurl_data.get("commentAllowed", 0)  # Max comment length

        if amount_msats < min_sendable:
            raise Exception(
                f"Amount {allowance.amount} sats is below minimum {min_sendable // 1000} sats"
            )
        if amount_msats > max_sendable:
            raise Exception(
                f"Amount {allowance.amount} sats exceeds maximum {max_sendable // 1000} sats"
            )

        # Step 3: Get invoice from LNURL-pay endpoint with appropriate memo
        logger.info(f"📋 Getting invoice for {allowance.amount} sats")

        # Prepare memo based on comment allowance
        memo = ""
        if comment_allowed > 0:
            desired_memo = allowance.memo or f"#allowance: {allowance.name}"
            memo = desired_memo[:comment_allowed]  # Truncate to allowed length
            if len(desired_memo) > comment_allowed:
                logger.info(f"⚠️ Memo truncated from {len(desired_memo)} to {comment_allowed} characters")
        else:
            logger.info(f"ℹ️ LNURL endpoint doesn't accept comments, sending without memo")

        payment_request = await get_invoice_from_lnurl(
            callback_url,
            amount_msats,
            memo,
        )

        # Step 4: Execute payment using LNBits pay_invoice
        logger.info(f"💸 Executing payment...")

        # Create a descriptive tag for the payment
        payment_tag = f"allowance: {allowance.name}"

        payment_result = await pay_invoice(
            wallet_id=allowance.wallet,
            payment_request=payment_request,
            extra={
                "tag": payment_tag,
                "allowance_id": allowance.id,
                "allowance_name": allowance.name,
                "lightning_address": allowance.lightning_address,
                "memo": allowance.memo or payment_tag,
                "scheduled": True,
            },
        )

        if payment_result:
            logger.info(f"✅ Payment successful for allowance: {allowance.name}")
            return True
        else:
            logger.error(f"❌ Payment failed for allowance: {allowance.name}")
            return False

    except Exception as e:
        logger.error(
            f"❌ Error executing payment for allowance {allowance.name}: {str(e)}"
        )
        return False


def ensure_timezone_aware(dt):
    """Helper to ensure datetime is timezone aware"""
    if dt and dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


async def check_and_process_allowances():
    """
    Background task to check and process scheduled allowance payments.
    Runs every 60 seconds (1 minute minimum frequency).
    """
    # Keep track of already deactivated allowances to prevent repeated processing
    deactivated_ids = set()

    while True:
        try:
            logger.info("🔄 Checking allowances for scheduled payments...")

            # Get all active allowances
            allowances = await get_all_active_allowances()
            current_time = datetime.now(timezone.utc)

            # Process each allowance
            for allowance in allowances:
                try:
                    # Skip if we've already deactivated this in a previous run
                    if allowance.id in deactivated_ids:
                        logger.debug(f"⏩ Skipping already-deactivated allowance: {allowance.name}")
                        continue

                    # The query already filters for active=true, so no need to check again

                    # Check if start_datetime hasn't been reached yet
                    if hasattr(allowance, "start_datetime") and allowance.start_datetime:
                        start_datetime = ensure_timezone_aware(allowance.start_datetime)
                        if current_time < start_datetime:
                            logger.info(f"⏳ Allowance {allowance.name} hasn't started yet (starts at {start_datetime})")
                            continue

                    # Check if end_datetime has passed
                    if hasattr(allowance, "end_datetime") and allowance.end_datetime:
                        end_datetime = ensure_timezone_aware(allowance.end_datetime)
                        if current_time > end_datetime:
                            logger.info(f"⏰ Allowance {allowance.name} has expired")
                            # Deactivate the expired allowance
                            await deactivate_allowance(allowance.id)
                            # Track that we've deactivated this one
                            deactivated_ids.add(allowance.id)
                            continue

                    # Check if payment is due
                    next_payment_date = ensure_timezone_aware(allowance.next_payment_date)

                    if current_time >= next_payment_date:
                        logger.info(
                            f"💸 Processing payment for allowance: {allowance.name}"
                        )

                        try:
                            # Execute Lightning address payment
                            success = await execute_lightning_address_payment(allowance)

                            if success:
                                # Update next payment date only if payment succeeded
                                if allowance.frequency_type == "minutely":
                                    allowance.next_payment_date = current_time + timedelta(
                                        minutes=1
                                    )
                                elif allowance.frequency_type == "hourly":
                                    allowance.next_payment_date = current_time + timedelta(
                                        hours=1
                                    )
                                elif allowance.frequency_type == "daily":
                                    allowance.next_payment_date = current_time + timedelta(
                                        days=1
                                    )
                                elif allowance.frequency_type == "weekly":
                                    allowance.next_payment_date = current_time + timedelta(
                                        weeks=1
                                    )
                                elif allowance.frequency_type == "monthly":
                                    allowance.next_payment_date = current_time + relativedelta(months=1)
                                elif allowance.frequency_type == "yearly":
                                    allowance.next_payment_date = current_time + relativedelta(years=1)

                                # Update the next payment date
                                await update_next_payment_date(allowance.id, allowance.next_payment_date)
                                logger.info(
                                    f"✅ Next payment scheduled for: {allowance.next_payment_date}"
                                )
                            else:
                                logger.error(f"❌ Payment failed, will retry on next cycle")

                        except Exception as e:
                            logger.error(
                                f"❌ Error processing allowance {allowance.name}: {e!s}"
                            )

                except Exception as e:
                    logger.error(f"❌ Error handling allowance {getattr(allowance, 'name', 'unknown')}: {str(e)}")
                    import traceback
                    logger.error(f"Traceback: {traceback.format_exc()}")

        except Exception as e:
            logger.error(f"❌ Error in allowance scheduler: {str(e)}")

        # Clean up deactivated list periodically (keep last 100 to prevent memory growth)
        if len(deactivated_ids) > 100:
            deactivated_ids = set(list(deactivated_ids)[-100:])

        # Check every 60 seconds (1 minute minimum payment frequency)
        await asyncio.sleep(60)


# This will be started by __init__.py when the extension loads
