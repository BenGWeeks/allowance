import asyncio
from datetime import datetime, timedelta
from typing import List

from lnbits.core.models import Payment
from lnbits.core.services import pay_invoice, websocket_updater
from lnbits.helpers import get_current_extension_name
from lnbits.tasks import register_invoice_listener
from loguru import logger

from .crud import get_all_active_allowances, get_allowance, update_allowance
from .models import Allowance

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
    await update_allowance(allowance)

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


async def check_and_process_allowances():
    """
    Background task to check and process scheduled allowance payments.
    Runs every 10 seconds.
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
                        await update_allowance(allowance)
                        continue

                # Check if payment is due
                if current_time >= allowance.next_payment_date:
                    logger.info(
                        f"💸 Processing payment for allowance: {allowance.name}"
                    )

                    try:
                        # Create invoice to lightning address
                        # NOTE: In a real implementation, you would:
                        # 1. Convert lightning address to LNURL
                        # 2. Get invoice from the LNURL endpoint
                        # 3. Pay the invoice

                        # For now, we'll log the payment attempt
                        logger.info(
                            f"💰 Would pay {allowance.amount} {allowance.currency} "
                            f"to {allowance.lightning_address}"
                        )

                        # Update next payment date
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
                            f"✅ Next payment scheduled for: "
                            f"{allowance.next_payment_date}"
                        )

                    except Exception as e:
                        logger.error(
                            f"❌ Error processing allowance {allowance.name}: {str(e)}"
                        )
            
        except Exception as e:
            logger.error(f"❌ Error in allowance scheduler: {str(e)}")
        
        # Check every 10 seconds
        await asyncio.sleep(10)


# This will be started by __init__.py when the extension loads
