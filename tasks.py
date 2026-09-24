import asyncio
import hashlib
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import quote

from lnbits.bolt11 import decode as decode_invoice
from lnbits.core.crud import get_standalone_payment
from lnbits.core.services import pay_invoice
from lnbits.core.services.payments import check_payment_status
from lnbits.utils.exchange_rates import fiat_amount_as_satoshis
from lnurl import decode as lnurl_decode
from loguru import logger

from .crud import (
    claim_payment,
    deactivate_allowance,
    defer_payment,
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


def lightning_address_url(lightning_address: str) -> str:
    if "@" not in lightning_address and lightning_address.lower().startswith("lnurl"):
        url = str(lnurl_decode(lightning_address))
    else:
        if lightning_address.count("@") != 1 or any(
            c.isspace() for c in lightning_address
        ):
            raise ValueError("Invalid Lightning address")
        user, domain = lightning_address.split("@")
        if not user or not domain or any(char in domain for char in "/?#\\[]"):
            raise ValueError("Invalid Lightning address")
        url = f"https://{domain}/.well-known/lnurlp/{quote(user, safe='')}"
    validate_url(url)
    return url


async def resolve_lightning_address(
    lightning_address: str,
) -> tuple[str, dict[str, Any]]:
    url = lightning_address_url(lightning_address)
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
    Return True/False for a terminal result, None while pending or retrying.
    """

    current = await get_allowance(allowance.id)
    if current is None or current.next_payment_date != allowance.next_payment_date:
        return None
    allowance.pending_payment_hash = current.pending_payment_hash
    if allowance.pending_payment_hash:
        return await reconcile_payment(allowance)
    if current.revision != allowance.revision or not current.active:
        return None
    now = datetime.now(timezone.utc)
    if current.next_payment_date > now or (
        current.retry_after and current.retry_after > now
    ):
        return None
    if current.retry_deadline and now >= current.retry_deadline:
        return False

    try:
        amount_sats = allowance.amount

        if allowance.currency and allowance.currency not in ["sats", "satoshis"]:

            amount_sats = await fiat_amount_as_satoshis(
                allowance.amount, allowance.currency.upper()
            )
        else:
            amount_sats = int(amount_sats)

        amount_msats = int(amount_sats * 1000)

        callback_url, lnurl_data = await resolve_lightning_address(
            allowance.lightning_address
        )

        min_sendable = lnurl_data.get("minSendable", 1000)
        max_sendable = lnurl_data.get("maxSendable", 100000000000)
        comment_allowed = lnurl_data.get("commentAllowed", 0)

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

        memo = ""
        if comment_allowed > 0:
            desired_memo = allowance.memo or ""
            memo = desired_memo[:comment_allowed]

        payment_request = await get_invoice_from_lnurl(
            callback_url,
            amount_msats,
            memo,
        )

        invoice = decode_invoice(payment_request)
        if invoice.amount_msat != amount_msats:
            raise ValueError("Invoice amount does not match the requested amount")
        if (
            invoice.description_hash
            != hashlib.sha256(lnurl_data["metadata"].encode()).hexdigest()
        ):
            raise ValueError("Invoice metadata hash mismatch")
        if invoice.has_expired():
            raise ValueError("Invoice expired")
        payment_hash = invoice.payment_hash
        previous = await get_standalone_payment(payment_hash)
        if previous and (previous.amount < 0 or previous.success):
            raise ValueError("Invoice was already used")
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
                "scheduled_at": int(allowance.next_payment_date.timestamp()),
            },
        )

        if not owns_payment(allowance, payment_result):
            raise ValueError("Invoice belongs to a different payment attempt")
        if payment_result.success:
            await update_allowance_success(
                allowance, int(datetime.now(timezone.utc).timestamp())
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
                allowance, error_msg, int(datetime.now(timezone.utc).timestamp())
            )
            return None if payment_result.pending else False

    except Exception:
        logger.error("Allowance payment attempt did not complete")
        await update_allowance_error(
            allowance,
            "Payment attempt failed; retrying if confirmed unsent",
            int(datetime.now(timezone.utc).timestamp()),
        )
        if allowance.pending_payment_hash:
            try:
                # Global lookup includes shared wallets and cannot hide an outgoing row.
                payment = await get_standalone_payment(allowance.pending_payment_hash)
            except Exception:
                return None
            if payment and owns_payment(allowance, payment):
                return await reconcile_payment(allowance)
        return await retry_unsent_payment(allowance)


async def retry_unsent_payment(allowance: Allowance) -> bool | None:
    now = datetime.now(timezone.utc)
    deadline = allowance.retry_deadline
    if deadline is None:
        deadline = now + timedelta(hours=24)
        following = next_occurrence(
            allowance.start_datetime,
            allowance.frequency_type,
            now,
            allowance.timezone_name,
        )
        if following is not None:
            deadline = min(deadline, following)
    if now >= deadline:
        return False
    delay = min(3600, 60 * 2 ** min(allowance.retry_count, 6))
    retry_at = min(deadline, now + timedelta(seconds=delay))
    await defer_payment(allowance, retry_at, deadline)
    return None


def owns_payment(allowance: Allowance, payment) -> bool:
    extra = payment.extra or {}
    return (
        payment.amount < 0
        and extra.get("allowance_id") == allowance.id
        and extra.get("scheduled_at", int(allowance.next_payment_date.timestamp()))
        == int(allowance.next_payment_date.timestamp())
    )


async def reconcile_payment(allowance: Allowance, refresh: bool = False) -> bool | None:
    """Inspect only the outgoing record belonging to this allowance occurrence."""
    if not allowance.pending_payment_hash:
        return None
    try:
        payment = await get_standalone_payment(allowance.pending_payment_hash)
        if payment is None or not owns_payment(allowance, payment):
            return None
        status = payment
        if payment.pending and refresh:
            status = await check_payment_status(payment)
    except Exception:
        logger.warning("Could not inspect allowance payment status")
        return None
    if status.pending:
        return None
    now = int(datetime.now(timezone.utc).timestamp())
    if status.success:
        updated = await update_allowance_success(allowance, now)
        return None if updated is False else True
    updated = await update_allowance_error(allowance, "Payment failed", now)
    return None if updated is False else False


async def process_allowance(allowance: Allowance, current_time: datetime):
    if allowance.pending_payment_hash:
        success = await reconcile_payment(allowance, refresh=True)
    else:
        if not allowance.active or current_time < allowance.start_datetime:
            return
        if allowance.end_datetime and current_time > allowance.end_datetime:
            await deactivate_allowance(allowance.id, revision=allowance.revision)
            return
        if current_time < allowance.next_payment_date:
            return
        if allowance.retry_after and current_time < allowance.retry_after:
            return
        success = await execute_lightning_address_payment(allowance)
    if success is None:
        return
    after = datetime.now(timezone.utc)
    if not success and allowance.retry_deadline and after >= allowance.retry_deadline:
        after = allowance.next_payment_date
    next_date = next_occurrence(
        allowance.start_datetime,
        allowance.frequency_type,
        after,
        allowance.timezone_name,
    )
    await finish_payment_attempt(allowance, next_date, success)


class AllowanceWorkers:
    def __init__(self):
        self.running: dict[str, asyncio.Task] = {}
        self.last_wallet: str | None = None
        self.last_allowance: dict[str, str] = {}

    def collect(self) -> bool:
        failed = False
        for wallet, task in list(self.running.items()):
            if task.done():
                del self.running[wallet]
                if task.cancelled() or task.exception():
                    failed = True
                    logger.error("Allowance operation: process_allowance")
        return failed

    async def poll(self, allowances: list[Allowance], now: datetime) -> bool:
        failed = self.collect()
        wallets = defaultdict(list)
        for allowance in allowances:
            if allowance.pending_payment_hash or (
                allowance.active
                and (
                    (allowance.end_datetime and allowance.end_datetime < now)
                    or (
                        allowance.next_payment_date <= now
                        and (not allowance.retry_after or allowance.retry_after <= now)
                    )
                )
            ):
                wallets[allowance.wallet].append(allowance)
        order = list(wallets)
        if self.last_wallet in order:
            offset = order.index(self.last_wallet) + 1
            order = order[offset:] + order[:offset]
        for wallet in order:
            if len(self.running) >= 8:
                break
            if wallet in self.running:
                continue
            records = wallets[wallet]
            previous = self.last_allowance.get(wallet)
            ids = [a.id for a in records]
            if previous in ids:
                offset = ids.index(previous) + 1
                records = records[offset:] + records[:offset]
            self.running[wallet] = asyncio.create_task(
                self.process_wallet(wallet, records[:5], now)
            )
            self.last_wallet = wallet
        if self.running:
            await asyncio.wait(self.running.values(), timeout=0)
        return self.collect() or failed

    async def process_wallet(self, wallet, records, now):
        for allowance in records:
            self.last_allowance[wallet] = allowance.id
            await process_allowance(allowance, now)

    async def close(self):
        for task in self.running.values():
            task.cancel()
        await asyncio.gather(*self.running.values(), return_exceptions=True)
        self.running.clear()


async def check_and_process_allowances():
    workers = AllowanceWorkers()
    try:
        while True:
            cycle_failed = False
            try:
                await record_scheduler_heartbeat("running")
                allowances = await get_all_active_allowances()
                cycle_failed = await workers.poll(
                    allowances, datetime.now(timezone.utc)
                )
            except Exception:
                cycle_failed = True
                logger.error("Allowance operation: check_and_process_allowances")
            try:
                await record_scheduler_heartbeat("error" if cycle_failed else "healthy")
            except Exception:
                logger.error("Could not record allowance scheduler heartbeat")
            await asyncio.sleep(60)
    finally:
        await workers.close()
