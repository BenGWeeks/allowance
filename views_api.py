from datetime import datetime, timezone
from http import HTTPStatus
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from lnbits.core.crud import get_user
from lnbits.core.models import Wallet
from lnbits.decorators import (
    require_admin_key,
    require_invoice_key,
)
from loguru import logger
from starlette.exceptions import HTTPException

from .crud import (
    create_allowance,
    delete_allowance,
    get_all_active_allowances,
    get_allowance,
    get_allowances,
    update_allowance,
)
from .models import CreateAllowanceData
from .tasks import execute_lightning_address_payment

allowance_api_router = APIRouter()

#######################################
##### API ENDPOINTS #####
#######################################


def get_wallet_id(wallet) -> str:
    """Helper to get wallet ID from either Wallet or WalletTypeInfo object."""
    if hasattr(wallet, "id"):
        return wallet.id
    elif hasattr(wallet, "wallet") and hasattr(wallet.wallet, "id"):
        return wallet.wallet.id
    else:
        raise ValueError("Cannot extract wallet ID from provided object")


def get_wallet_user(wallet) -> str:
    """Helper to get wallet user from either Wallet or WalletTypeInfo object."""
    if hasattr(wallet, "user"):
        return wallet.user
    elif hasattr(wallet, "wallet") and hasattr(wallet.wallet, "user"):
        return wallet.wallet.user
    else:
        raise ValueError("Cannot extract wallet user from provided object")


def parse_datetime_string(date_str: Optional[str]) -> Optional[datetime]:
    """Helper to parse datetime strings from various formats."""
    if not date_str:
        return None

    # Handle empty strings
    if date_str.strip() == "":
        return None

    # First try parsing ISO format with timezone offset like +00:00
    # Python's isoformat() produces this format
    if "+" in date_str or date_str.endswith("Z"):
        try:
            # Replace +00:00 with +0000 for strptime %z
            normalized = date_str.replace("+00:00", "+0000").replace("-00:00", "-0000")
            if normalized.endswith("Z"):
                normalized = normalized[:-1] + "+0000"

            # Try with microseconds first
            try:
                dt = datetime.strptime(normalized, "%Y-%m-%dT%H:%M:%S.%f%z")
                return dt
            except ValueError:
                # Try without microseconds
                dt = datetime.strptime(normalized, "%Y-%m-%dT%H:%M:%S%z")
                return dt
        except ValueError:
            pass

    # Try different formats
    formats = [
        "%Y-%m-%dT%H:%M:%S.%f",  # ISO format without timezone
        "%Y-%m-%dT%H:%M:%S",  # ISO format without microseconds
        "%Y-%m-%dT%H:%M",  # datetime-local format
        "%Y-%m-%d %H:%M:%S",  # Alternative format
    ]

    for fmt in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            # Make timezone aware
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            continue

    # Try parsing as timestamp
    try:
        timestamp = float(date_str)
        return datetime.fromtimestamp(timestamp, tz=timezone.utc)
    except (ValueError, TypeError):
        pass

    logger.warning(f"Could not parse datetime string: {date_str}")
    return None


## Get wallet info for current user
@allowance_api_router.get("/api/v1/wallet-info", status_code=HTTPStatus.OK)
async def api_wallet_info(
    wallet: Wallet = Depends(require_invoice_key),
):
    """Get basic wallet info for the current user."""
    wallet_id = get_wallet_id(wallet)

    return {
        "id": wallet_id,
        "name": (
            getattr(wallet, "name", "Wallet")
            if hasattr(wallet, "name")
            else (
                getattr(wallet.wallet, "name", "Wallet")
                if hasattr(wallet, "wallet")
                else "Wallet"
            )
        ),
        "adminkey": (
            getattr(wallet, "adminkey", "")
            if hasattr(wallet, "adminkey")
            else (
                getattr(wallet.wallet, "adminkey", "")
                if hasattr(wallet, "wallet")
                else ""
            )
        ),
        "inkey": (
            getattr(wallet, "inkey", "")
            if hasattr(wallet, "inkey")
            else (
                getattr(wallet.wallet, "inkey", "") if hasattr(wallet, "wallet") else ""
            )
        ),
    }


## Get all the records belonging to the user
@allowance_api_router.get("/api/v1/allowance", status_code=HTTPStatus.OK)
async def api_allowances(
    wallet: Wallet = Depends(require_admin_key),
    all_wallets: bool = Query(False),
):
    """Get allowances for the authenticated wallet or all wallets (if admin)."""
    wallet_id = get_wallet_id(wallet)
    logger.info(f"🔗 API called: Getting allowances for wallet {wallet_id}")

    try:
        if all_wallets:
            # For admin viewing all wallets, get all active allowances
            allowances = await get_all_active_allowances()
        else:
            # Get allowances for specific wallet
            allowances = await get_allowances(wallet_id)

        # Convert to list of dicts with proper datetime formatting
        result = []
        for allowance in allowances:
            data = allowance.dict()

            # Format datetime fields for API response
            for field in [
                "start_datetime",
                "end_datetime",
                "next_payment_date",
                "created_at",
            ]:
                if data.get(field):
                    if isinstance(data[field], datetime):
                        data[field] = data[field].isoformat()
                    elif isinstance(data[field], (int, float)):
                        # Convert timestamp to ISO format
                        data[field] = datetime.fromtimestamp(
                            data[field], tz=timezone.utc
                        ).isoformat()

            result.append(data)

        logger.info(f"✅ Returning {len(result)} allowances")
        return result

    except Exception as e:
        logger.error(f"❌ Error getting allowances: {e}")
        return []


## Get a specific record by ID
@allowance_api_router.get("/api/v1/allowance/{allowance_id}", status_code=HTTPStatus.OK)
async def api_allowance(
    allowance_id: str,
    wallet: Wallet = Depends(require_invoice_key),
):
    """Get a specific allowance by ID."""
    allowance = await get_allowance(allowance_id)

    if not allowance:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Allowance not found"
        )

    # Check ownership
    if allowance.wallet != get_wallet_id(wallet):
        raise HTTPException(
            status_code=HTTPStatus.FORBIDDEN,
            detail="Not authorized to view this allowance",
        )

    data = allowance.dict()

    # Format datetime fields
    for field in ["start_datetime", "end_datetime", "next_payment_date", "created_at"]:
        if data.get(field):
            if isinstance(data[field], datetime):
                data[field] = data[field].isoformat()
            elif isinstance(data[field], (int, float)):
                data[field] = datetime.fromtimestamp(
                    data[field], tz=timezone.utc
                ).isoformat()

    return data


## Update a record
@allowance_api_router.put("/api/v1/allowance/{allowance_id}", status_code=HTTPStatus.OK)
async def api_allowance_update(
    allowance_id: str,
    request: Request,
    wallet: Wallet = Depends(require_admin_key),
):
    """Update an existing allowance."""
    # Get existing allowance
    allowance = await get_allowance(allowance_id)
    if not allowance:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Allowance not found"
        )

    # Check ownership
    if allowance.wallet != get_wallet_id(wallet):
        user = await get_user(get_wallet_user(wallet))
        if not user or not user.super_user:
            raise HTTPException(
                status_code=HTTPStatus.FORBIDDEN,
                detail="Not authorized to update this allowance",
            )

    # Parse request data
    data = await request.json()
    logger.info(f"📝 Update request for allowance {allowance_id}: {data}")

    # Handle datetime fields
    start_dt = parse_datetime_string(data.get("start_datetime"))
    end_dt = parse_datetime_string(data.get("end_datetime"))

    # Validate start_datetime is provided (now mandatory)
    if start_dt is None:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail="start_datetime is required",
        )

    # Validate: cannot change start_datetime on existing allowances
    if start_dt != allowance.start_datetime:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail="Cannot change start_datetime of existing allowance",
        )

    # Validate: cannot change frequency_type on existing allowances
    if data.get("frequency_type") and data.get("frequency_type") != allowance.frequency_type:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail="Cannot change frequency_type of existing allowance",
        )

    # Validate: cannot activate if end_datetime is in the past
    is_active = data.get("active", allowance.active)
    if is_active and end_dt is not None:
        current_time = datetime.now(timezone.utc)
        if end_dt < current_time:
            raise HTTPException(
                status_code=HTTPStatus.BAD_REQUEST,
                detail="Cannot activate allowance: end_datetime is in the past",
            )

    # Calculate next payment date
    # If the allowance is being activated or if next_payment_date is in the past,
    # set it to now so payments start immediately
    was_inactive = not allowance.active
    is_being_activated = was_inactive and is_active

    # Check if next_payment_date is in the past
    next_payment_in_past = False
    if allowance.next_payment_date:
        try:
            if isinstance(allowance.next_payment_date, datetime):
                next_payment_datetime = allowance.next_payment_date
            else:
                next_payment_datetime = datetime.fromtimestamp(
                    allowance.next_payment_date, tz=timezone.utc
                )
            current_time = datetime.now(timezone.utc)
            next_payment_in_past = next_payment_datetime < current_time
        except Exception as e:
            logger.warning(f"⚠️ Error parsing next_payment_date: {e}")
            next_payment_in_past = True

    # If being activated or next payment is in the past, reset to now
    if is_being_activated or next_payment_in_past:
        next_payment = datetime.now(timezone.utc)
        logger.info(
            f"🔄 Resetting next_payment_date to NOW for allowance {allowance_id}"
        )
    else:
        # Use the provided start_datetime
        next_payment = start_dt

    # Create update data
    update_data = CreateAllowanceData(
        id=allowance_id,
        wallet=allowance.wallet,  # Keep original wallet
        name=data.get("name", allowance.name),
        lightning_address=data.get("lightning_address", allowance.lightning_address),
        amount=data.get("amount", allowance.amount),
        currency=data.get("currency", allowance.currency),
        start_datetime=start_dt,
        frequency_type=data.get("frequency_type", allowance.frequency_type),
        next_payment_date=next_payment,
        memo=data.get("memo", allowance.memo),
        active=data.get("active", allowance.active),
        end_datetime=end_dt,
        lnurlpay=data.get("lnurlpay", allowance.lnurlpay),
        total=data.get("total", allowance.total),
        created_at=allowance.created_at,  # Keep original created_at
    )

    # Update in database
    try:
        updated = await update_allowance(update_data)
        logger.info(f"✅ Updated allowance {allowance_id}")

        # Format response
        result = updated.dict()
        for field in [
            "start_datetime",
            "end_datetime",
            "next_payment_date",
            "created_at",
        ]:
            if result.get(field):
                if isinstance(result[field], datetime):
                    result[field] = result[field].isoformat()
                elif isinstance(result[field], (int, float)):
                    result[field] = datetime.fromtimestamp(
                        result[field], tz=timezone.utc
                    ).isoformat()

        return result

    except Exception as e:
        logger.error(f"❌ Error updating allowance: {e}")
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail=f"Failed to update allowance: {e!s}",
        ) from e


## Create a new record
@allowance_api_router.post("/api/v1/allowance", status_code=HTTPStatus.CREATED)
async def api_allowance_create(
    request: Request,
    wallet: Wallet = Depends(require_admin_key),
):
    """Create a new allowance."""
    data = await request.json()
    wallet_id = get_wallet_id(wallet)
    logger.info(f"📝 Create request from wallet {wallet_id}: {data}")

    # Handle datetime fields
    start_dt = parse_datetime_string(data.get("start_datetime"))
    end_dt = parse_datetime_string(data.get("end_datetime"))

    # Validate start_datetime is provided (now mandatory)
    if start_dt is None:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail="start_datetime is required",
        )

    # Validate: cannot activate if end_datetime is in the past
    is_active = data.get("active", True)
    if is_active and end_dt is not None:
        current_time = datetime.now(timezone.utc)
        if end_dt < current_time:
            raise HTTPException(
                status_code=HTTPStatus.BAD_REQUEST,
                detail="Cannot activate allowance: end_datetime is in the past",
            )

    # Calculate next payment date
    next_payment = start_dt

    # Create new allowance data
    create_data = CreateAllowanceData(
        wallet=wallet_id,
        name=data.get("name"),
        lightning_address=data.get("lightning_address"),
        amount=data.get("amount", 0),
        currency=data.get("currency", "sats"),
        start_datetime=start_dt,
        frequency_type=data.get("frequency_type", "daily"),
        next_payment_date=next_payment,
        memo=data.get("memo", ""),
        active=is_active,
        end_datetime=end_dt,
        lnurlpay=data.get("lnurlpay", ""),
        total=data.get("total", 0),
        created_at=datetime.now(timezone.utc),
    )

    # Validate required fields
    if not create_data.name or not create_data.lightning_address:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail="Name and lightning_address are required",
        )

    # Create in database
    try:
        allowance = await create_allowance(create_data)
        logger.info(f"✅ Created allowance {allowance.id}")

        # Format response
        result = allowance.dict()
        for field in [
            "start_datetime",
            "end_datetime",
            "next_payment_date",
            "created_at",
        ]:
            if result.get(field):
                if isinstance(result[field], datetime):
                    result[field] = result[field].isoformat()
                elif isinstance(result[field], (int, float)):
                    result[field] = datetime.fromtimestamp(
                        result[field], tz=timezone.utc
                    ).isoformat()

        return result

    except Exception as e:
        logger.error(f"❌ Error creating allowance: {e}")
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail=f"Failed to create allowance: {e!s}",
        ) from e


## Delete a record
@allowance_api_router.delete(
    "/api/v1/allowance/{allowance_id}", status_code=HTTPStatus.OK
)
async def api_allowance_delete(
    allowance_id: str,
    wallet: Wallet = Depends(require_admin_key),
):
    """Delete an allowance."""
    # Get existing allowance
    allowance = await get_allowance(allowance_id)
    if not allowance:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Allowance not found"
        )

    # Check ownership
    if allowance.wallet != get_wallet_id(wallet):
        user = await get_user(get_wallet_user(wallet))
        if not user or not user.super_user:
            raise HTTPException(
                status_code=HTTPStatus.FORBIDDEN,
                detail="Not authorized to delete this allowance",
            )

    # Delete from database
    try:
        await delete_allowance(allowance_id)
        logger.info(f"✅ Deleted allowance {allowance_id}")
        return {"message": f"Allowance {allowance_id} deleted successfully"}

    except Exception as e:
        logger.error(f"❌ Error deleting allowance: {e}")
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete allowance: {e!s}",
        ) from e


## Get currency conversion rate
@allowance_api_router.get("/api/v1/rate/{currency}", status_code=HTTPStatus.OK)
async def api_currency_rate(
    currency: str,
    wallet: Wallet = Depends(require_invoice_key),
):
    """Get currency conversion rate to sats."""
    import httpx

    try:
        # Use CoinGecko API for conversion rates
        async with httpx.AsyncClient() as client:
            # Get Bitcoin price in the requested currency
            response = await client.get(
                "https://api.coingecko.com/api/v3/simple/price",
                params={"ids": "bitcoin", "vs_currencies": currency.lower()},
            )
            response.raise_for_status()
            data = response.json()

            if "bitcoin" not in data or currency.lower() not in data["bitcoin"]:
                raise HTTPException(
                    status_code=HTTPStatus.BAD_REQUEST,
                    detail=f"Currency {currency} not supported",
                )

            # Calculate sats per unit of currency
            btc_price = data["bitcoin"][currency.lower()]
            sats_per_unit = 100_000_000 / btc_price  # 100M sats per BTC

            return {
                "currency": currency.upper(),
                "rate": sats_per_unit,
                "btc_price": btc_price,
            }

    except httpx.HTTPError as e:
        logger.error(f"Error fetching currency rate: {e}")
        raise HTTPException(
            status_code=HTTPStatus.SERVICE_UNAVAILABLE,
            detail="Could not fetch currency rate",
        ) from e
    except Exception as e:
        logger.error(f"Error processing currency rate: {e}")
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail=f"Error processing currency rate: {e!s}",
        ) from e


## Manual trigger for testing scheduled payments
@allowance_api_router.post(
    "/api/v1/allowance/{allowance_id}/trigger", status_code=HTTPStatus.OK
)
async def api_allowance_trigger(
    allowance_id: str,
    wallet: Wallet = Depends(require_admin_key),
):
    """Manually trigger a payment for an allowance (for testing)."""
    # Get the allowance
    allowance = await get_allowance(allowance_id)
    if not allowance:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Allowance not found"
        )

    # Check ownership
    if allowance.wallet != get_wallet_id(wallet):
        user = await get_user(get_wallet_user(wallet))
        if not user or not user.super_user:
            raise HTTPException(
                status_code=HTTPStatus.FORBIDDEN,
                detail="Not authorized to trigger this allowance",
            )

    # Execute the payment
    try:
        logger.info(f"🚀 Manually triggering payment for allowance: {allowance.name}")
        success = await execute_lightning_address_payment(allowance)

        if success:
            return {
                "success": True,
                "message": f"Payment triggered successfully for {allowance.name}",
                "amount": allowance.amount,
                "lightning_address": allowance.lightning_address,
            }
        else:
            raise HTTPException(
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
                detail="Payment execution failed",
            )

    except Exception as e:
        logger.error(f"Error triggering payment: {e}")
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail=f"Failed to trigger payment: {e!s}",
        ) from e


## Verify scheduled payments are working
@allowance_api_router.post(
    "/api/v1/allowance/test-scheduler", status_code=HTTPStatus.OK
)
async def api_test_scheduler(
    wallet: Wallet = Depends(require_admin_key),
):
    """Test that the scheduler is running and can see allowances."""
    try:
        # Get all active allowances
        allowances = await get_all_active_allowances()

        # Filter to user's allowances
        user_allowances = [a for a in allowances if a.wallet == get_wallet_id(wallet)]

        # Check which are due
        now = datetime.now(timezone.utc)
        due_allowances = []
        upcoming_allowances = []

        for allowance in user_allowances:
            # Handle next_payment_date as either datetime or timestamp
            next_payment = allowance.next_payment_date
            if isinstance(next_payment, (int, float)):
                next_payment = datetime.fromtimestamp(next_payment, tz=timezone.utc)
            elif next_payment and next_payment.tzinfo is None:
                next_payment = next_payment.replace(tzinfo=timezone.utc)

            if next_payment and next_payment <= now:
                due_allowances.append(
                    {
                        "id": allowance.id,
                        "name": allowance.name,
                        "next_payment": (
                            next_payment.isoformat() if next_payment else None
                        ),
                        "amount": allowance.amount,
                        "lightning_address": allowance.lightning_address,
                    }
                )
            else:
                upcoming_allowances.append(
                    {
                        "id": allowance.id,
                        "name": allowance.name,
                        "next_payment": (
                            next_payment.isoformat() if next_payment else None
                        ),
                        "amount": allowance.amount,
                        "lightning_address": allowance.lightning_address,
                    }
                )

        return {
            "scheduler_status": "running",
            "total_active_allowances": len(allowances),
            "user_active_allowances": len(user_allowances),
            "due_for_payment": due_allowances,
            "upcoming_payments": upcoming_allowances,
            "current_time": now.isoformat(),
        }

    except Exception as e:
        logger.error(f"Error testing scheduler: {e}")
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail=f"Error testing scheduler: {e!s}",
        ) from e
