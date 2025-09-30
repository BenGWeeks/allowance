import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
from dateutil.relativedelta import relativedelta  # type: ignore[import-untyped]
from lnbits.core.crud import get_standalone_payment, update_payment
from lnbits.core.services import pay_invoice
from lnurl import decode as lnurl_decode
from loguru import logger

from .crud import (
    deactivate_allowance,
    get_all_active_allowances,
    update_allowance_error,
    update_allowance_success,
    update_next_payment_date,
)
from .models import Allowance


async def resolve_lightning_address(
    lightning_address: str,
) -> tuple[str, dict[str, Any]]:
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
            raise Exception(f"Invalid LNURL: {lightning_address}") from e

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
        raise Exception(
            f"Failed to resolve Lightning address: {lightning_address}"
        ) from e
    except Exception as e:
        logger.error(f"Error resolving Lightning address {lightning_address}: {e}")
        raise Exception(
            f"Failed to resolve Lightning address: {lightning_address}"
        ) from e


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
        raise Exception("Failed to get invoice from LNURL endpoint") from e
    except Exception as e:
        logger.error(f"Error getting invoice from LNURL: {e}")
        raise Exception("Failed to get invoice from LNURL endpoint") from e


async def execute_lightning_address_payment(allowance: Allowance) -> bool:
    """
    Execute payment to Lightning address
    Returns True if successful, False otherwise
    """
    try:
        # Convert amount to sats if using fiat currency
        amount_sats = allowance.amount

        if allowance.currency and allowance.currency not in ["sats", "satoshis"]:
            # Need to convert fiat to sats
            logger.info(
                f"💱 Converting {allowance.amount} {allowance.currency} to sats"
            )

            # Get exchange rate from CoinGecko API
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://api.coingecko.com/api/v3/simple/price",
                    params={
                        "ids": "bitcoin",
                        "vs_currencies": allowance.currency.lower(),
                    },
                )
                response.raise_for_status()
                data = response.json()

                if "bitcoin" in data and allowance.currency.lower() in data["bitcoin"]:
                    btc_price_in_currency = data["bitcoin"][allowance.currency.lower()]
                    # Convert: amount in currency -> BTC -> sats
                    btc_amount = allowance.amount / btc_price_in_currency
                    amount_sats = int(btc_amount * 100_000_000)  # Convert BTC to sats
                    logger.info(
                        f"💱 Converted to {amount_sats} sats "
                        f"(rate: 1 BTC = {btc_price_in_currency} {allowance.currency})"
                    )
                else:
                    raise Exception(
                        f"Could not get exchange rate for {allowance.currency}"
                    )
        else:
            # Already in sats, ensure integer
            amount_sats = int(amount_sats)

        # Convert sats to millisatoshis (ensure integer)
        amount_msats = int(amount_sats * 1000)

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
            currency_display = (
                f"{allowance.amount} {allowance.currency}"
                if allowance.currency and allowance.currency != "sats"
                else f"{allowance.amount} sats"
            )
            raise Exception(
                f"Amount {currency_display} ({amount_sats} sats) is below minimum "
                f"{min_sendable // 1000} sats"
            )
        if amount_msats > max_sendable:
            currency_display = (
                f"{allowance.amount} {allowance.currency}"
                if allowance.currency and allowance.currency != "sats"
                else f"{allowance.amount} sats"
            )
            raise Exception(
                f"Amount {currency_display} ({amount_sats} sats) exceeds maximum "
                f"{max_sendable // 1000} sats"
            )

        # Step 3: Get invoice from LNURL-pay endpoint with appropriate memo
        currency_display = (
            f"{allowance.amount} {allowance.currency}"
            if allowance.currency and allowance.currency != "sats"
            else f"{amount_sats} sats"
        )
        logger.info(f"📋 Getting invoice for {currency_display} ({amount_sats} sats)")

        # Prepare memo based on comment allowance
        memo = ""
        if comment_allowed > 0:
            desired_memo = allowance.memo or f"#allowance: {allowance.name}"
            memo = desired_memo[:comment_allowed]  # Truncate to allowed length
            if len(desired_memo) > comment_allowed:
                logger.info(
                    f"⚠️ Memo truncated from {len(desired_memo)} to "
                    f"{comment_allowed} characters"
                )
        else:
            logger.info(
                "ℹ️ LNURL endpoint doesn't accept comments, "  # noqa: RUF001
                "sending without memo"
            )

        payment_request = await get_invoice_from_lnurl(
            callback_url,
            amount_msats,
            memo,
        )

        # Step 4: Execute payment using LNBits pay_invoice
        logger.info("💸 Executing payment...")

        payment_result = await pay_invoice(
            wallet_id=allowance.wallet,
            payment_request=payment_request,
            extra={
                "tag": "allowance",
                "allowance_id": allowance.id,
                "allowance_name": allowance.name,
                "lightning_address": allowance.lightning_address,
                "scheduled": True,
            },
        )

        if payment_result:
            # Update the payment memo field
            payment = await get_standalone_payment(payment_result.checking_id)
            if payment:
                payment.memo = allowance.name
                await update_payment(payment)
            # Clear any previous errors and record success
            await update_allowance_success(
                allowance.id, int(datetime.now(timezone.utc).timestamp())
            )
            logger.info(f"✅ Payment successful for allowance: {allowance.name}")
            return True
        else:
            error_msg = "Payment failed"
            logger.error(f"❌ Payment failed for allowance: {allowance.name}")
            await update_allowance_error(
                allowance.id, error_msg, int(datetime.now(timezone.utc).timestamp())
            )
            return False

    except Exception as e:
        error_msg = str(e)
        logger.error(
            f"❌ Error executing payment for allowance {allowance.name}: {error_msg}"
        )
        # Store error information
        await update_allowance_error(
            allowance.id, error_msg, int(datetime.now(timezone.utc).timestamp())
        )
        return False


def ensure_timezone_aware(dt):
    """Helper to ensure datetime is timezone aware"""
    if dt and dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


async def check_and_process_allowances():  # noqa: C901
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
            logger.info(f"📊 Found {len(allowances)} active allowances to process")
            current_time = datetime.now(timezone.utc)

            # Process each allowance
            for allowance in allowances:
                try:
                    logger.debug(
                        f"🔍 Checking allowance: {allowance.name} (ID: {allowance.id[:8]}...)"
                    )

                    # Skip if we've already deactivated this in a previous run
                    if allowance.id in deactivated_ids:
                        logger.debug(
                            f"⏩ Skipping already-deactivated allowance: "
                            f"{allowance.name}"
                        )
                        continue

                    # The query already filters for active=true,
                    # so no need to check again

                    # Check if start_datetime hasn't been reached yet
                    if (
                        hasattr(allowance, "start_datetime")
                        and allowance.start_datetime
                    ):
                        start_datetime = ensure_timezone_aware(allowance.start_datetime)
                        if current_time < start_datetime:
                            logger.info(
                                f"⏳ Allowance {allowance.name} hasn't started yet "
                                f"(starts at {start_datetime})"
                            )
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
                    next_payment_date = ensure_timezone_aware(
                        allowance.next_payment_date
                    )

                    logger.debug(
                        f"⏰ {allowance.name}: next_payment={next_payment_date}, current={current_time}, due={current_time >= next_payment_date}"
                    )

                    if current_time >= next_payment_date:
                        logger.info(
                            f"💸 Processing payment for allowance: {allowance.name}"
                        )

                        try:
                            # Execute Lightning address payment
                            success = await execute_lightning_address_payment(allowance)

                            # Update next payment date regardless of success/failure
                            # This ensures the schedule continues even if a payment fails
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
                                allowance.next_payment_date = (
                                    current_time + relativedelta(months=1)
                                )
                            elif allowance.frequency_type == "yearly":
                                allowance.next_payment_date = (
                                    current_time + relativedelta(years=1)
                                )

                            # Update the next payment date in database
                            await update_next_payment_date(
                                allowance.id, allowance.next_payment_date
                            )

                            if success:
                                logger.info(
                                    f"✅ Next payment scheduled for: "
                                    f"{allowance.next_payment_date}"
                                )
                            else:
                                logger.error(
                                    f"❌ Payment failed. Next attempt scheduled for: "
                                    f"{allowance.next_payment_date}"
                                )

                        except Exception as e:
                            logger.error(
                                f"❌ Error processing allowance {allowance.name}: {e!s}"
                            )

                except Exception as e:
                    logger.error(
                        f"❌ Error handling allowance "
                        f"{getattr(allowance, 'name', 'unknown')}: {e!s}"
                    )
                    import traceback

                    logger.error(f"Traceback: {traceback.format_exc()}")

        except Exception as e:
            logger.error(f"❌ Error in allowance scheduler: {e!s}")

        # Clean up deactivated list periodically
        # (keep last 100 to prevent memory growth)
        if len(deactivated_ids) > 100:
            deactivated_ids = set(list(deactivated_ids)[-100:])

        # Check every 60 seconds (1 minute minimum payment frequency)
        await asyncio.sleep(60)


# This will be started by __init__.py when the extension loads
