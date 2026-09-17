import asyncio
from datetime import datetime, timezone
from typing import Any
from urllib.parse import quote

from lnbits.bolt11 import decode as decode_invoice
from lnbits.core.crud import get_standalone_payment
from lnbits.core.services import pay_invoice
from lnbits.core.services.payments import check_transaction_status
from lnbits.exceptions import PaymentError
from lnbits.utils.exchange_rates import fiat_amount_as_satoshis
from lnurl import decode as lnurl_decode
from loguru import logger

from .crud import (
    claim_payment,
    deactivate_allowance,
    finish_payment_attempt,
    get_all_active_allowances,
    get_allowance,
    record_scheduler_heartbeat,
    update_allowance_error,
    update_allowance_success,
)
from .models import Allowance
from .safe_http import get_public_json, validate_url
from .schedule import next_occurrence


async def resolve_lightning_address(
    lightning_address: str,
) -> tuple[str, dict[str, Any]]:
    if lightning_address.lower().startswith("lnurl"):
        url = str(lnurl_decode(lightning_address))
    else:
        if lightning_address.count("@") != 1:
            raise ValueError("Invalid Lightning address")
        user, domain = lightning_address.split("@")
        if not user or not domain or any(char in domain for char in "/?#\\"):
            raise ValueError("Invalid Lightning address")
        url = f"https://{domain}/.well-known/lnurlp/{quote(user, safe='')}"
    data = await get_public_json(url)
    minimum, maximum = data.get("minSendable"), data.get("maxSendable")
    if (
        data.get("tag") != "payRequest"
        or type(minimum) is not int
        or type(maximum) is not int
        or not 0 < minimum <= maximum
        or not isinstance(data.get("metadata"), str)
    ):
        raise ValueError("Invalid LNURL-pay response")
    callback = data.get("callback")
    if not isinstance(callback, str):
        raise ValueError("Missing LNURL callback")
    validate_url(callback)
    comment_allowed = data.get("commentAllowed", 0)
    if type(comment_allowed) is not int or not 0 <= comment_allowed <= 10000:
        raise ValueError("Invalid LNURL comment limit")
    return callback, data


async def get_invoice_from_lnurl(
    callback_url: str, amount_msats: int, memo: str = ""
) -> str:
    params: dict[str, int | str] = {"amount": amount_msats}
    if memo:
        params["comment"] = memo
    data = await get_public_json(callback_url, params=params)
    if data.get("status") == "ERROR":
        raise ValueError("LNURL endpoint rejected the invoice request")
    invoice = data.get("pr")
    if not isinstance(invoice, str) or not invoice:
        raise ValueError("Missing LNURL invoice")
    return invoice


async def execute_lightning_address_payment(  # noqa: C901
    allowance: Allowance,
) -> bool | None:
    """
    Execute payment to Lightning address
    Return True for success, False for terminal failure, None while unresolved.
    """
    # Refresh persisted state: another worker/manual request may already own it.
    current = await get_allowance(allowance.id)
    if current is None or current.next_payment_date != allowance.next_payment_date:
        return None
    allowance.pending_payment_hash = current.pending_payment_hash
    if allowance.pending_payment_hash:
        return await reconcile_payment(allowance)
    if current.revision != allowance.revision or not current.active:
        return None

    try:
        # Convert amount to sats if using fiat currency
        amount_sats = allowance.amount

        if allowance.currency and allowance.currency not in ["sats", "satoshis"]:
            # Need to convert fiat to sats

            amount_sats = await fiat_amount_as_satoshis(
                allowance.amount, allowance.currency.upper()
            )
        else:
            # Already in sats, ensure integer
            amount_sats = int(amount_sats)

        # Convert sats to millisatoshis (ensure integer)
        amount_msats = int(amount_sats * 1000)

        # Step 1: Resolve Lightning address to LNURL-pay endpoint
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
        # Prepare memo based on comment allowance
        memo = ""
        if comment_allowed > 0:
            desired_memo = allowance.memo or f"#allowance: {allowance.name}"
            memo = desired_memo[:comment_allowed]  # Truncate to allowed length

        payment_request = await get_invoice_from_lnurl(
            callback_url,
            amount_msats,
            memo,
        )

        # Step 4: Execute payment using LNBits pay_invoice

        invoice = decode_invoice(payment_request)
        if invoice.amount_msat != amount_msats:
            raise ValueError("Invoice amount does not match the requested amount")
        payment_hash = invoice.payment_hash
        if not await claim_payment(allowance, payment_hash):
            return None
        allowance.pending_payment_hash = payment_hash
        payment_result = await pay_invoice(
            wallet_id=allowance.wallet,
            payment_request=payment_request,
            max_sat=amount_sats,
            description=memo or allowance.name,
            tag="allowance",
            extra={
                "tag": "allowance",
                "allowance_id": allowance.id,
                "allowance_name": allowance.name,
                "lightning_address": allowance.lightning_address,
                "scheduled": True,
            },
        )

        if payment_result.success:
            # Clear any previous errors and record success
            await update_allowance_success(
                allowance.id, int(datetime.now(timezone.utc).timestamp())
            )
            return True
        else:
            error_msg = (
                "Payment pending settlement"
                if payment_result.pending
                else "Payment failed"
            )
            logger.error("Allowance operation: execute_lightning_address_payment")
            await update_allowance_error(
                allowance.id, error_msg, int(datetime.now(timezone.utc).timestamp())
            )
            return None if payment_result.pending else False

    except PaymentError as e:
        # LNbits explicitly marks preflight rejection and terminal funding-source
        # failure as failed. Unknown outcomes retain the persisted claim.
        await update_allowance_error(
            allowance.id,
            (
                "Payment rejected"
                if e.status == "failed"
                else "Payment outcome unresolved"
            ),
            int(datetime.now(timezone.utc).timestamp()),
        )
        return False if e.status == "failed" else None
    except Exception:
        error_msg = "Payment processing failed; check payment status before retrying"
        logger.error("Allowance operation: execute_lightning_address_payment")
        # Store error information
        await update_allowance_error(
            allowance.id, error_msg, int(datetime.now(timezone.utc).timestamp())
        )
        return None if allowance.pending_payment_hash else False


async def reconcile_payment(allowance: Allowance, refresh: bool = False) -> bool | None:
    """Inspect an existing claim only; never request or send a new invoice."""
    if not allowance.pending_payment_hash:
        return None
    payment = await get_standalone_payment(
        allowance.pending_payment_hash, wallet_id=allowance.wallet
    )
    if payment is None:
        return None
    status = payment
    if payment.pending and refresh:
        status = await check_transaction_status(
            allowance.wallet, allowance.pending_payment_hash
        )
    if status.pending:
        return None
    now = int(datetime.now(timezone.utc).timestamp())
    if status.success:
        await update_allowance_success(allowance.id, now)
        return True
    await update_allowance_error(allowance.id, "Payment failed", now)
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

    while True:
        cycle_failed = False
        try:
            await record_scheduler_heartbeat("running")

            # Get all active allowances
            allowances = await get_all_active_allowances()
            current_time = datetime.now(timezone.utc)

            # Process each allowance
            for allowance in allowances:
                try:

                    # The query already filters for active=true,
                    # so no need to check again

                    # Check if start_datetime hasn't been reached yet
                    if (
                        hasattr(allowance, "start_datetime")
                        and allowance.start_datetime
                    ):
                        start_datetime = ensure_timezone_aware(allowance.start_datetime)
                        if current_time < start_datetime:
                            continue

                    # Check if end_datetime has passed
                    if hasattr(allowance, "end_datetime") and allowance.end_datetime:
                        end_datetime = ensure_timezone_aware(allowance.end_datetime)
                        if current_time > end_datetime:
                            # Deactivate the expired allowance
                            await deactivate_allowance(allowance.id)
                            # Track that we've deactivated this one
                            continue

                    # Check if payment is due
                    next_payment_date = ensure_timezone_aware(
                        allowance.next_payment_date
                    )

                    if current_time >= next_payment_date:

                        try:
                            # Validate recurrence before attempting a payment.
                            next_occurrence(
                                allowance.start_datetime,
                                allowance.frequency_type,
                                current_time,
                            )
                            # Execute Lightning address payment
                            success = await execute_lightning_address_payment(allowance)

                            if success is None:
                                # Reconcile pending payments before advancing.
                                continue

                            # Keep the original cadence after every attempt.
                            # Use completion time so a slow attempt cannot leave the
                            # next occurrence in the past and trigger a catch-up burst.
                            next_date = next_occurrence(
                                allowance.start_datetime,
                                allowance.frequency_type,
                                datetime.now(timezone.utc),
                            )

                            if next_date is None:
                                # One-off attempts finish only after a terminal result.
                                # Retrying could duplicate an unsettled payment.
                                await finish_payment_attempt(allowance, None, success)
                                continue
                            await finish_payment_attempt(allowance, next_date, success)
                            allowance.next_payment_date = next_date

                            if not success:
                                logger.error(
                                    "Allowance operation: check_and_process_allowances"
                                )

                        except Exception:
                            cycle_failed = True
                            logger.error(
                                "Allowance operation: check_and_process_allowances"
                            )

                except Exception:
                    cycle_failed = True
                    logger.error("Allowance operation: check_and_process_allowances")

        except Exception:
            cycle_failed = True
            logger.error("Allowance operation: check_and_process_allowances")

        try:
            await record_scheduler_heartbeat("error" if cycle_failed else "healthy")
        except Exception:
            logger.error("Could not record allowance scheduler heartbeat")

        # Check every 60 seconds (1 minute minimum payment frequency)
        await asyncio.sleep(60)


# This will be started by __init__.py when the extension loads
