import asyncio
import httpx
from datetime import datetime, timedelta
from typing import List, Tuple, Dict, Any

from lnbits.core.models import Payment
from lnbits.core.services import websocket_updater, pay_invoice
from lnbits.helpers import get_current_extension_name
from lnbits.tasks import register_invoice_listener
from loguru import logger
from lnurl import decode as lnurl_decode

from .crud import get_all_active_allowances, get_allowance, update_allowance
from .models import CreateAllowanceData, Allowance

#######################################
########## RUN YOUR TASKS HERE ########
#######################################

# The usual task is to listen to invoices related to this extension


async def wait_for_paid_invoices():
    invoice_queue = asyncio.Queue()
    register_invoice_listener(invoice_queue, get_current_extension_name())
    while True:
        payment = await invoice_queue.get()
        await on_invoice_paid(payment)


# Do somethhing when an invoice related top this extension is paid


async def on_invoice_paid(payment: Payment) -> None:
    if payment.extra.get("tag") != "Allowance":
        return

    allowance_id = payment.extra.get("allowanceId")
    assert allowance_id, "allowanceId not set in invoice"
    allowance = await get_allowance(allowance_id)
    assert allowance, "Allowance does not exist"

    # update something in the db
    if payment.extra.get("lnurlwithdraw"):
        total = allowance.total - payment.amount
    else:
        total = allowance.total + payment.amount

    allowance.total = total
    update_data = CreateAllowanceData(**allowance.dict())
    await update_allowance(update_data)

    # here we could send some data to a websocket on
    # wss://<your-lnbits>/api/v1/ws/<allowance_id> and then listen to it on
    # the frontend, which we do with index.html connectWebocket()

    some_payment_data = {
        "name": allowance.name,
        "amount": payment.amount,
        "fee": payment.fee,
        "checking_id": payment.checking_id,
    }

    await websocket_updater(allowance_id, str(some_payment_data))


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
        params = {
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

        # Step 2: Validate amount limits (if provided by LNURL endpoint)
        min_sendable = lnurl_data.get("minSendable", 1000)  # Default 1 sat minimum
        max_sendable = lnurl_data.get(
            "maxSendable", 100000000000
        )  # Default 100k sats max

        if amount_msats < min_sendable:
            raise Exception(
                f"Amount {allowance.amount} sats is below minimum {min_sendable // 1000} sats"
            )
        if amount_msats > max_sendable:
            raise Exception(
                f"Amount {allowance.amount} sats exceeds maximum {max_sendable // 1000} sats"
            )

        # Step 3: Get invoice from LNURL-pay endpoint
        logger.info(f"📋 Getting invoice for {allowance.amount} sats")
        payment_request = await get_invoice_from_lnurl(
            callback_url,
            amount_msats,
            allowance.memo or f"Allowance payment: {allowance.name}",
        )

        # Step 4: Execute payment using LNBits pay_invoice
        logger.info(f"💸 Executing payment...")
        payment_result = await pay_invoice(
            wallet_id=allowance.wallet,
            payment_request=payment_request,
            extra={
                "tag": "allowance",
                "allowance_id": allowance.id,
                "lightning_address": allowance.lightning_address,
                "memo": allowance.memo,
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


async def check_and_process_allowances():
    """
    Background task to check and process scheduled allowance payments.
    Runs every 60 seconds (1 minute minimum frequency).
    """
    while True:
        try:
            logger.info("🔄 Checking allowances for scheduled payments...")

            # Get all active allowances
            allowances = await get_all_active_allowances()
            current_time = datetime.utcnow()

            for allowance in allowances:
                # Skip inactive allowances
                if not getattr(allowance, "active", True):
                    continue

                # Check if end_date has passed
                if hasattr(allowance, "end_date") and allowance.end_date:
                    if current_time > allowance.end_date:
                        logger.info(f"⏰ Allowance {allowance.name} has expired")
                        allowance.active = False
                        update_data = CreateAllowanceData(**allowance.dict())
                        await update_allowance(update_data)
                        continue

                # Check if payment is due
                if current_time >= allowance.next_payment_date:
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
                                allowance.next_payment_date = current_time + timedelta(
                                    days=30
                                )
                            elif allowance.frequency_type == "yearly":
                                allowance.next_payment_date = current_time + timedelta(
                                    days=365
                                )

                            await update_allowance(allowance)
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
            logger.error(f"❌ Error in allowance scheduler: {str(e)}")

        # Check every 60 seconds (1 minute minimum payment frequency)
        await asyncio.sleep(60)


# This will be started by __init__.py when the extension loads
