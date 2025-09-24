from http import HTTPStatus

from fastapi import APIRouter, Depends, Query, Request
from loguru import logger
from lnbits.core.crud import get_user

# from lnbits.core.models import WalletTypeInfo  # Not available in LNbits v1.0
from lnbits.core.services import create_invoice
from lnbits.decorators import (
    get_wallet_for_key,
    require_admin_key,
    require_invoice_key,
)
from lnbits.helpers import urlsafe_short_hash
from lnurl import encode as lnurl_encode
from starlette.exceptions import HTTPException

from .crud import (
    create_allowance,
    delete_allowance,
    get_allowance,
    get_allowances,
    update_allowance,
)
from .models import CreateAllowanceData, Allowance

allowance_api_router = APIRouter()

#######################################
##### ADD YOUR API ENDPOINTS HERE #####
#######################################

## Get all the records belonging to the user


@allowance_api_router.get(
    "/api/v1/allowance", status_code=HTTPStatus.OK, response_model=None
)
async def api_allowances(
    request: Request,
    all_wallets: bool = Query(False),
):
    # Manual authentication check to avoid Pydantic issues
    api_key = request.headers.get("X-Api-Key")
    if not api_key:
        raise HTTPException(status_code=401, detail="API key required")

    # Validate the API key and get wallet
    try:
        from lnbits.core.models import Wallet
        from lnbits.core.crud import get_wallet_for_key

        wallet = await get_wallet_for_key(api_key)
        if not wallet:
            raise HTTPException(status_code=401, detail="Invalid API key")
    except Exception as e:
        logger.warning(f"Authentication failed: {e}")
        raise HTTPException(status_code=401, detail="Authentication failed")

    # Get real allowances from database
    logger.info(f"🔗 API called: Getting allowances for wallet {wallet.id}")

    try:
        import asyncpg

        # Connect to database
        conn = await asyncpg.connect(
            "postgresql://lnbits:password@allowance-postgres:5432/lnbits"
        )

        # Get allowances for this wallet (only select columns that exist)
        if all_wallets:
            # Admin can see all allowances
            rows = await conn.fetch(
                """
                SELECT id, name, wallet, lightning_address, amount, currency,
                       start_datetime, frequency_type, next_payment_date, memo,
                       active, end_datetime, created_at
                FROM ext_allowance.maintable
                ORDER BY created_at DESC, id DESC
            """
            )
        else:
            # Filter by wallet ID
            rows = await conn.fetch(
                """
                SELECT id, name, wallet, lightning_address, amount, currency,
                       start_datetime, frequency_type, next_payment_date, memo,
                       active, end_datetime, created_at
                FROM ext_allowance.maintable
                WHERE wallet = $1
                ORDER BY created_at DESC, id DESC
            """,
                wallet.id,
            )

        await conn.close()

        # Convert to list of dicts
        allowances = []
        for row in rows:
            allowance_dict = {
                "id": row["id"],
                "name": row["name"],
                "wallet": row["wallet"],
                "lightning_address": row["lightning_address"],
                "amount": row["amount"],
                "currency": row["currency"],
                "start_datetime": (
                    row["start_datetime"].isoformat() if row["start_datetime"] else None
                ),
                "frequency_type": row["frequency_type"],
                "next_payment_date": (
                    row["next_payment_date"].isoformat()
                    if row["next_payment_date"]
                    else None
                ),
                "memo": row["memo"] or "",
                "active": row["active"],
                "end_datetime": row["end_datetime"].isoformat() if row["end_datetime"] else None,
                "created_at": (
                    row["created_at"].isoformat() if row["created_at"] else None
                ),
                "lnurlpay": None,  # Column doesn't exist in table
                "total": 0,  # Column doesn't exist in table
            }
            allowances.append(allowance_dict)

        logger.info(f"📊 Returning {len(allowances)} allowances")
        return allowances

    except Exception as e:
        logger.error(f"🚨 Database error in api_allowances: {e}")
        return []


## Get a single record


@allowance_api_router.get(
    "/api/v1/allowance/{allowance_id}",
    status_code=HTTPStatus.OK,
    response_model=None,
)
async def api_allowance(request: Request, allowance_id: str):
    # Manual authentication check to avoid Pydantic issues
    api_key = request.headers.get("X-Api-Key")
    if not api_key:
        raise HTTPException(status_code=401, detail="API key required")

    # Validate the API key and get wallet
    try:
        from lnbits.core.crud import get_wallet_for_key

        wallet = await get_wallet_for_key(api_key)
        if not wallet:
            raise HTTPException(status_code=401, detail="Invalid API key")
    except Exception as e:
        logger.warning(f"Authentication failed: {e}")
        raise HTTPException(status_code=401, detail="Authentication failed")

    allowance = await get_allowance(allowance_id)
    if not allowance:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Allowance does not exist."
        )

    # Verify wallet ownership
    if allowance.wallet != wallet.id:
        raise HTTPException(
            status_code=HTTPStatus.FORBIDDEN, detail="Not your Allowance."
        )

    return allowance.dict()


## update a record


@allowance_api_router.put("/api/v1/allowance/{allowance_id}", response_model=None)
async def api_allowance_update(
    request: Request,
    data: CreateAllowanceData,
    allowance_id: str,
):
    # Manual authentication check to avoid Pydantic issues
    api_key = request.headers.get("X-Api-Key")
    if not api_key:
        raise HTTPException(status_code=401, detail="API key required")

    # Validate the API key and get wallet
    try:
        from lnbits.core.crud import get_wallet_for_key

        wallet = await get_wallet_for_key(api_key)
        if not wallet:
            raise HTTPException(status_code=401, detail="Invalid API key")
    except Exception as e:
        logger.warning(f"Authentication failed: {e}")
        raise HTTPException(status_code=401, detail="Authentication failed")

    if not allowance_id:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Allowance does not exist."
        )

    # Get existing allowance and update using direct database query
    try:
        import asyncpg
        from datetime import datetime

        def parse_datetime_string(date_input):
            """Parse datetime input (string or datetime object) to timezone-naive datetime"""
            if not date_input:
                return None
            try:
                # If already a datetime object, just remove timezone info
                if isinstance(date_input, datetime):
                    return date_input.replace(tzinfo=None)

                # If it's a string, parse it
                if isinstance(date_input, str):
                    # Remove 'Z' suffix and parse as UTC
                    if date_input.endswith("Z"):
                        date_input = date_input[:-1] + "+00:00"
                    # Parse ISO format and remove timezone
                    dt = datetime.fromisoformat(date_input)
                    return dt.replace(tzinfo=None)

                # If it's something else, try to convert to string first
                date_str = str(date_input)
                dt = datetime.fromisoformat(date_str)
                return dt.replace(tzinfo=None)

            except Exception as e:
                logger.warning(
                    f"Error parsing datetime '{date_input}' (type: {type(date_input)}): {e}"
                )
                return None

        # Connect to database
        conn = await asyncpg.connect(
            "postgresql://lnbits:password@allowance-postgres:5432/lnbits"
        )

        # Check if allowance exists and verify ownership
        row = await conn.fetchrow(
            """
            SELECT wallet FROM ext_allowance.maintable 
            WHERE id = $1
            """,
            allowance_id,
        )

        if not row:
            await conn.close()
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND, detail="Allowance does not exist."
            )

        # Verify wallet ownership
        if row["wallet"] != wallet.id:
            await conn.close()
            raise HTTPException(
                status_code=HTTPStatus.FORBIDDEN, detail="Not your Allowance."
            )

        # Parse datetime fields
        # If start_datetime is not provided, keep existing value (don't overwrite with None)
        from datetime import datetime, timezone
        start_datetime = parse_datetime_string(data.start_datetime) if data.start_datetime else row["start_datetime"]
        next_payment_date = (
            parse_datetime_string(data.next_payment_date)
            if data.next_payment_date
            else None
        )
        end_datetime = parse_datetime_string(data.end_datetime) if data.end_datetime else None

        # Update the allowance
        await conn.execute(
            """
            UPDATE ext_allowance.maintable 
            SET name = $2, lightning_address = $3, amount = $4, currency = $5,
                start_datetime = $6, frequency_type = $7, next_payment_date = $8, 
                memo = $9, active = $10, end_datetime = $11
            WHERE id = $1
            """,
            allowance_id,
            data.name,
            data.lightning_address,
            data.amount,
            data.currency,
            start_datetime,
            data.frequency_type,
            next_payment_date,
            data.memo,
            data.active,
            end_datetime,
        )

        await conn.close()

        logger.info(f"✅ Updated allowance: {allowance_id}")
        return {
            "id": allowance_id,
            "name": data.name,
            "message": "Allowance updated successfully",
        }

    except HTTPException:
        # Re-raise HTTP exceptions (404, 403) as-is
        raise
    except Exception as e:
        logger.error(f"🚨 Database error in api_allowance_update: {e}")
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail=f"Failed to update allowance: {str(e)}",
        )


## Create a new record


@allowance_api_router.post(
    "/api/v1/allowance", status_code=HTTPStatus.CREATED, response_model=None
)
async def api_allowance_create(
    request: Request,
    data: CreateAllowanceData,
):
    # Manual authentication check to avoid Pydantic issues
    api_key = request.headers.get("X-Api-Key")
    if not api_key:
        raise HTTPException(status_code=401, detail="API key required")

    # Validate the API key and get wallet
    try:
        from lnbits.core.crud import get_wallet_for_key

        wallet = await get_wallet_for_key(api_key)
        if not wallet:
            raise HTTPException(status_code=401, detail="Invalid API key")
    except Exception as e:
        logger.warning(f"Authentication failed: {e}")
        raise HTTPException(status_code=401, detail="Authentication failed")

    # Create allowance in database
    logger.info(f"🔗 API called: Creating allowance for wallet {wallet.id}")
    try:
        import asyncpg

        # Generate ID
        data.id = urlsafe_short_hash()

        # Parse datetime strings to proper datetime objects
        from datetime import datetime
        import re

        def parse_datetime_string(date_input):
            """Parse datetime input (string or datetime object) to timezone-naive datetime"""
            if not date_input:
                return None
            try:
                # If already a datetime object, just remove timezone info
                if isinstance(date_input, datetime):
                    return date_input.replace(tzinfo=None)

                # If it's a string, parse it
                if isinstance(date_input, str):
                    # Remove 'Z' suffix and parse as UTC
                    if date_input.endswith("Z"):
                        date_input = date_input[:-1] + "+00:00"
                    # Parse ISO format and remove timezone
                    dt = datetime.fromisoformat(date_input)
                    return dt.replace(tzinfo=None)

                # If it's something else, try to convert to string first
                date_str = str(date_input)
                dt = datetime.fromisoformat(date_str)
                return dt.replace(tzinfo=None)

            except Exception as e:
                logger.warning(
                    f"Error parsing datetime '{date_input}' (type: {type(date_input)}): {e}"
                )
                return None

        # If start_datetime is not provided, default to now for new allowances
        from datetime import datetime, timezone
        start_datetime = parse_datetime_string(data.start_datetime) if data.start_datetime else datetime.now(timezone.utc)
        next_payment_date = (
            parse_datetime_string(data.next_payment_date)
            if data.next_payment_date
            else None
        )
        end_datetime = parse_datetime_string(data.end_datetime) if data.end_datetime else None

        # Connect to database
        conn = await asyncpg.connect(
            "postgresql://lnbits:password@allowance-postgres:5432/lnbits"
        )

        # Insert new allowance (created_at will be set automatically by DEFAULT CURRENT_TIMESTAMP)
        await conn.execute(
            """
            INSERT INTO ext_allowance.maintable 
            (id, name, wallet, lightning_address, amount, currency, start_datetime, 
             frequency_type, next_payment_date, memo, active, end_datetime)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
            """,
            data.id,
            data.name,
            wallet.id,
            data.lightning_address,
            data.amount,
            data.currency,
            start_datetime,
            data.frequency_type,
            next_payment_date,
            data.memo,
            data.active,
            end_datetime,
        )

        await conn.close()

        logger.info(f"✅ Created allowance: {data.id}")
        return {
            "id": data.id,
            "name": data.name,
            "message": "Allowance created successfully",
        }

    except Exception as e:
        logger.error(f"🚨 Error creating allowance: {e}")
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail=f"Failed to create allowance: {str(e)}",
        )
    # data.id = urlsafe_short_hash()
    # data.wallet = data.wallet or wallet.id
    # new_allowance = await create_allowance(data)
    # return new_allowance.dict()


## Delete a record


@allowance_api_router.delete("/api/v1/allowance/{allowance_id}", response_model=None)
async def api_allowance_delete(
    request: Request,
    allowance_id: str,
):
    # Manual authentication check to avoid Pydantic issues
    api_key = request.headers.get("X-Api-Key")
    if not api_key:
        raise HTTPException(status_code=401, detail="API key required")

    # Validate the API key and get wallet
    try:
        from lnbits.core.crud import get_wallet_for_key

        wallet = await get_wallet_for_key(api_key)
        if not wallet:
            raise HTTPException(status_code=401, detail="Invalid API key")
    except Exception as e:
        logger.warning(f"Authentication failed: {e}")
        raise HTTPException(status_code=401, detail="Authentication failed")

    # Get allowance and verify ownership using direct database query
    try:
        import asyncpg

        # Connect to database
        conn = await asyncpg.connect(
            "postgresql://lnbits:password@allowance-postgres:5432/lnbits"
        )

        # Check if allowance exists and get wallet
        logger.info(f"🔍 Looking for allowance: {allowance_id}")
        row = await conn.fetchrow(
            """
            SELECT wallet FROM ext_allowance.maintable 
            WHERE id = $1
            """,
            allowance_id,
        )

        logger.info(f"🔍 Query result: {row}")

        if not row:
            await conn.close()
            logger.warning(f"❌ Allowance not found: {allowance_id}")
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND, detail="Allowance does not exist."
            )

        # Verify wallet ownership
        if row["wallet"] != wallet.id:
            await conn.close()
            raise HTTPException(
                status_code=HTTPStatus.FORBIDDEN, detail="Not your Allowance."
            )

        # Delete the allowance
        await conn.execute(
            """
            DELETE FROM ext_allowance.maintable 
            WHERE id = $1
            """,
            allowance_id,
        )

        await conn.close()

        logger.info(f"✅ Deleted allowance: {allowance_id}")
        return {"message": "Allowance deleted successfully"}

    except HTTPException:
        # Re-raise HTTP exceptions (404, 403) as-is
        raise
    except Exception as e:
        logger.error(f"🚨 Database error in api_allowance_delete: {e}")
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete allowance: {str(e)}",
        )


# ANY OTHER ENDPOINTS YOU NEED

## Currency exchange rate endpoint for dynamic currency support
## (currencies list comes from core LNBits /api/v1/currencies)


# @allowance_api_router.get("/api/v1/rate/{currency}", status_code=HTTPStatus.OK)
# async def api_check_fiat_rate(currency: str) -> dict:
#     try:
#         rate = await get_fiat_rate_satoshis(currency)
#     except AssertionError:
#         rate = None
#     return {"rate": rate}


## This endpoint creates a payment


@allowance_api_router.post(
    "/api/v1/allowance/payment/{allowance_id}",
    status_code=HTTPStatus.CREATED,
    response_model=None,
)
async def api_allowance_create_invoice(
    allowance_id: str, amount: int = Query(..., ge=1), memo: str = ""
):
    allowance = await get_allowance(allowance_id)

    if not allowance:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Allowance does not exist."
        )

    # we create a payment and add some tags,
    # so tasks.py can grab the payment once its paid

    try:
        payment_hash, payment_request = await create_invoice(
            wallet_id=allowance.wallet,
            amount=amount,
            memo=f"{memo} to {allowance.name}" if memo else f"{allowance.name}",
            extra={
                "tag": "allowance",
                "amount": amount,
            },
        )
    except Exception as exc:
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR, detail=str(exc)
        ) from exc

    return {"payment_hash": payment_hash, "payment_request": payment_request}


## Manual trigger endpoint for development - process scheduled payments


@allowance_api_router.post(
    "/api/v1/allowance/trigger_payments",
    status_code=HTTPStatus.OK,
    response_model=None,
)
async def api_trigger_scheduled_payments():
    """
    Manual trigger for scheduled payments processing - for development use.
    This runs the same logic as the background scheduler.
    """
    try:
        from .tasks import check_and_process_allowances
        from .crud import get_all_active_allowances
        from datetime import datetime, timezone
        import asyncio

        logger.info("🔧 Manual trigger: Processing scheduled payments...")

        # Get all active allowances
        allowances = await get_all_active_allowances()
        current_time = datetime.now(timezone.utc)

        processed_count = 0
        success_count = 0

        for allowance in allowances:
            # Skip inactive allowances
            if not getattr(allowance, "active", True):
                continue

            # Check if payment is due (ensure timezone awareness)
            next_payment_date = allowance.next_payment_date
            if next_payment_date.tzinfo is None:
                next_payment_date = next_payment_date.replace(tzinfo=timezone.utc)

            if current_time >= next_payment_date:
                logger.info(f"💸 Processing payment for allowance: {allowance.name}")
                processed_count += 1

                try:
                    from .tasks import execute_lightning_address_payment
                    from .models import CreateAllowanceData
                    from .crud import update_allowance
                    from datetime import timedelta
                    from dateutil.relativedelta import relativedelta

                    # Execute Lightning address payment
                    success = await execute_lightning_address_payment(allowance)

                    if success:
                        success_count += 1
                        # Update next payment date
                        if allowance.frequency_type == "minutely":
                            allowance.next_payment_date = current_time + timedelta(minutes=1)
                        elif allowance.frequency_type == "hourly":
                            allowance.next_payment_date = current_time + timedelta(hours=1)
                        elif allowance.frequency_type == "daily":
                            allowance.next_payment_date = current_time + timedelta(days=1)
                        elif allowance.frequency_type == "weekly":
                            allowance.next_payment_date = current_time + timedelta(weeks=1)
                        elif allowance.frequency_type == "monthly":
                            allowance.next_payment_date = current_time + relativedelta(months=1)
                        elif allowance.frequency_type == "yearly":
                            allowance.next_payment_date = current_time + relativedelta(years=1)

                        # Convert to CreateAllowanceData for update
                        update_data = CreateAllowanceData(
                            id=allowance.id,
                            name=allowance.name,
                            wallet=allowance.wallet,
                            lightning_address=allowance.lightning_address,
                            amount=allowance.amount,
                            currency=allowance.currency,
                            start_datetime=allowance.start_datetime,
                            frequency_type=allowance.frequency_type,
                            next_payment_date=allowance.next_payment_date,
                            memo=allowance.memo or "",
                            active=allowance.active,
                            end_datetime=allowance.end_datetime,
                            total=allowance.total or 0
                        )
                        await update_allowance(update_data)
                        logger.info(f"✅ Payment successful, next payment: {allowance.next_payment_date}")
                    else:
                        logger.error(f"❌ Payment failed for allowance: {allowance.name}")

                except Exception as e:
                    logger.error(f"❌ Error processing allowance {allowance.name}: {e}")

        result = {
            "message": "Payment processing completed",
            "total_allowances": len(allowances),
            "processed_count": processed_count,
            "success_count": success_count,
            "timestamp": current_time.isoformat()
        }

        logger.info(f"🎯 Manual trigger completed: {result}")
        return result

    except Exception as e:
        logger.error(f"❌ Error in manual payment trigger: {str(e)}")
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail=f"Payment processing failed: {str(e)}"
        )
