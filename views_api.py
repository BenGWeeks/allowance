from datetime import datetime, timedelta, timezone
from http import HTTPStatus

from fastapi import APIRouter, Depends, Query
from lnbits.core.crud import get_user
from lnbits.core.models import Wallet, WalletTypeInfo
from lnbits.decorators import (
    require_admin_key,
    require_invoice_key,
)
from loguru import logger
from starlette.exceptions import HTTPException

from .crud import (
    AllowanceConflictError,
    create_allowance,
    delete_allowance,
    get_all_active_allowances,
    get_allowance,
    get_allowances,
    update_allowance,
)
from .models import AllowanceCreateRequest, AllowanceUpdateRequest, CreateAllowanceData
from .tasks import execute_lightning_address_payment

allowance_api_router = APIRouter()

#######################################
##### API ENDPOINTS #####
#######################################


def get_wallet_id(wallet: Wallet | WalletTypeInfo) -> str:
    """Authentication dependencies return WalletTypeInfo, wrapping the wallet."""
    return wallet.wallet.id if isinstance(wallet, WalletTypeInfo) else wallet.id


def get_wallet_user(wallet: Wallet | WalletTypeInfo) -> str:
    return wallet.wallet.user if isinstance(wallet, WalletTypeInfo) else wallet.user


## Get wallet info for current user
@allowance_api_router.get("/api/v1/wallet-info", status_code=HTTPStatus.OK)
async def api_wallet_info(
    wallet: WalletTypeInfo = Depends(require_invoice_key),
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
    }


## Get all the records belonging to the user
@allowance_api_router.get("/api/v1/allowance", status_code=HTTPStatus.OK)
async def api_allowances(  # noqa: C901
    wallet: WalletTypeInfo = Depends(require_admin_key),
    all_wallets: bool = Query(False),
):
    """Get allowances for all of the user's wallets."""
    wallet_user = get_wallet_user(wallet)

    try:
        # Get user to access all their wallets
        user = await get_user(wallet_user)
        if not user:
            logger.error("Allowance operation: api_allowances")
            return []

        # Get all wallet IDs for this user
        user_wallet_ids = [w.id for w in user.wallets]

        if all_wallets and not user.super_user:
            raise HTTPException(
                status_code=HTTPStatus.FORBIDDEN,
                detail="Only the superuser can view all users' allowances",
            )

        if all_wallets:
            # For admin viewing all wallets, get all active allowances
            allowances = await get_all_active_allowances()
        else:
            # Get allowances for all of the user's wallets
            allowances = await get_allowances(user_wallet_ids)

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

        return result

    except HTTPException:
        raise
    except Exception:
        logger.error("Allowance operation: api_allowances")
        raise HTTPException(503, "Could not load allowances") from None


## Get a specific record by ID
@allowance_api_router.get("/api/v1/allowance/{allowance_id}", status_code=HTTPStatus.OK)
async def api_allowance(
    allowance_id: str,
    wallet: WalletTypeInfo = Depends(require_invoice_key),
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


def validate_schedule_input(data: dict):
    """Validate dates together, including existing fields on a partial update."""
    end = data.get("end_datetime")
    if end is not None and end < data["start_datetime"]:
        raise HTTPException(422, "end_datetime must not precede start_datetime")
    if (
        data.get("active", True)
        and end is not None
        and end < datetime.now(timezone.utc)
    ):
        raise HTTPException(
            422, "Cannot activate an allowance whose end date has passed"
        )
    if (
        data.get("currency", "sats") in ("sats", "satoshis")
        and not float(data["amount"]).is_integer()
    ):
        raise HTTPException(422, "Satoshi amounts must be whole numbers")


@allowance_api_router.put("/api/v1/allowance/{allowance_id}")
async def api_allowance_update(
    allowance_id: str,
    data: AllowanceUpdateRequest,
    wallet: WalletTypeInfo = Depends(require_admin_key),
):
    allowance = await get_allowance(allowance_id)
    if not allowance:
        raise HTTPException(404, "Allowance not found")
    if allowance.wallet != get_wallet_id(wallet):
        user = await get_user(get_wallet_user(wallet))
        if not user or not user.super_user:
            raise HTTPException(403, "Not authorized to update this allowance")
    changes = data.dict(exclude_unset=True)
    for field in ("id", "wallet", "start_datetime", "frequency_type"):
        if field in changes and changes[field] != getattr(allowance, field):
            raise HTTPException(422, f"Cannot change {field} of an existing allowance")
    merged = {**allowance.dict(), **changes}
    if merged.get("memo") is None:
        merged["memo"] = ""
    if merged.get("total") is None:
        merged["total"] = 0
    validate_schedule_input(merged)
    try:
        updated = await update_allowance(CreateAllowanceData(**merged))
        return updated.dict()
    except AllowanceConflictError as exc:
        raise HTTPException(409, str(exc)) from exc


@allowance_api_router.post("/api/v1/allowance", status_code=HTTPStatus.CREATED)
async def api_allowance_create(
    data: AllowanceCreateRequest,
    wallet: WalletTypeInfo = Depends(require_admin_key),
):
    wallet_id = get_wallet_id(wallet)
    if data.wallet is not None and data.wallet != wallet_id:
        raise HTTPException(403, "Wallet does not match the authenticated wallet")
    now = datetime.now(timezone.utc)
    if data.start_datetime < now + timedelta(minutes=1):
        raise HTTPException(
            422, "start_datetime must be at least 1 minute in the future"
        )
    values = data.dict(exclude={"id", "revision", "wallet"})
    validate_schedule_input(values)
    allowance = await create_allowance(
        CreateAllowanceData(
            **values,
            wallet=wallet_id,
            next_payment_date=data.start_datetime,
            created_at=now,
        )
    )
    return allowance.dict()


## Delete a record
@allowance_api_router.delete(
    "/api/v1/allowance/{allowance_id}", status_code=HTTPStatus.OK
)
async def api_allowance_delete(
    allowance_id: str,
    wallet: WalletTypeInfo = Depends(require_admin_key),
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
        return {"message": f"Allowance {allowance_id} deleted successfully"}

    except Exception as e:
        logger.error("Allowance operation: api_allowance_delete")
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail="Failed to delete allowance",
        ) from e


## Get currency conversion rate
@allowance_api_router.get("/api/v1/rate/{currency}", status_code=HTTPStatus.OK)
async def api_currency_rate(
    currency: str,
    wallet: WalletTypeInfo = Depends(require_invoice_key),
):
    """Get currency conversion rate to sats."""
    from lnbits.utils.exchange_rates import (
        allowed_currencies,
        get_fiat_rate_and_price_satoshis,
    )

    if currency.upper() not in allowed_currencies():
        raise HTTPException(status_code=400, detail="Unsupported currency")
    try:
        rate, price = await get_fiat_rate_and_price_satoshis(currency.upper())
        if not (rate > 0 and price > 0):
            raise ValueError("LNbits returned an unavailable fiat quote")
        return {"currency": currency.upper(), "rate": rate, "btc_price": price}
    except Exception as e:
        logger.warning("Allowance operation: api_currency_rate")
        raise HTTPException(
            status_code=HTTPStatus.SERVICE_UNAVAILABLE,
            detail="Could not fetch currency rate",
        ) from e


## Manual trigger for testing scheduled payments
@allowance_api_router.post(
    "/api/v1/allowance/{allowance_id}/trigger", status_code=HTTPStatus.OK
)
async def api_allowance_trigger(
    allowance_id: str,
    wallet: WalletTypeInfo = Depends(require_admin_key),
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
        success = await execute_lightning_address_payment(allowance)

        if success is None:
            return {
                "success": False,
                "pending": True,
                "message": "Payment outcome unresolved; no new invoice sent",
            }
        from .crud import finish_payment_attempt
        from .schedule import next_occurrence

        await finish_payment_attempt(
            allowance,
            next_occurrence(
                allowance.start_datetime,
                allowance.frequency_type,
                datetime.now(timezone.utc),
            ),
            success,
        )
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
        logger.error("Allowance operation: api_allowance_trigger")
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail="Failed to trigger payment",
        ) from e


## Verify scheduled payments are working
@allowance_api_router.post(
    "/api/v1/allowance/test-scheduler", status_code=HTTPStatus.OK
)
async def api_test_scheduler(
    wallet: WalletTypeInfo = Depends(require_admin_key),
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
            "total_active_allowances": len(user_allowances),
            "user_active_allowances": len(user_allowances),
            "due_for_payment": due_allowances,
            "upcoming_payments": upcoming_allowances,
            "current_time": now.isoformat(),
        }

    except Exception as e:
        logger.error("Allowance operation: api_test_scheduler")
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail="Error testing scheduler",
        ) from e


@allowance_api_router.post("/api/v1/allowance/{allowance_id}/reconcile")
async def api_allowance_reconcile(
    allowance_id: str, wallet: WalletTypeInfo = Depends(require_admin_key)
):
    """Check a claimed payment without initiating a new payment, even if paused."""
    from .crud import finish_payment_attempt
    from .schedule import next_occurrence
    from .tasks import reconcile_payment

    allowance = await get_allowance(allowance_id)
    if not allowance:
        raise HTTPException(404, "Allowance not found")
    if allowance.wallet != get_wallet_id(wallet):
        raise HTTPException(403, "Not authorized to reconcile this allowance")
    if not allowance.pending_payment_hash:
        return {"pending": False, "message": "No unresolved payment"}
    result = await reconcile_payment(allowance, refresh=True)
    if result is None:
        return {
            "pending": True,
            "message": "Payment remains unresolved. No new payment was sent. "
            "If LNbits has no record, ask the server operator to verify the "
            "funding-source payment before changing the claim.",
        }
    await finish_payment_attempt(
        allowance,
        next_occurrence(
            allowance.start_datetime,
            allowance.frequency_type,
            datetime.now(timezone.utc),
        ),
        result,
    )
    return {
        "pending": False,
        "success": result,
        "message": "Payment status confirmed; schedule updated",
    }


@allowance_api_router.get("/api/v1/allowance/{allowance_id}/history")
async def api_allowance_history(
    allowance_id: str,
    wallet: WalletTypeInfo = Depends(require_invoice_key),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    from .crud import get_payment_history

    allowance = await get_allowance(allowance_id)
    if not allowance:
        raise HTTPException(404, "Allowance not found")
    if allowance.wallet != get_wallet_id(wallet):
        raise HTTPException(403, "Not authorized to view this history")
    return await get_payment_history(allowance_id, limit, offset)


@allowance_api_router.get("/api/v1/health")
async def api_allowance_health(wallet: WalletTypeInfo = Depends(require_invoice_key)):
    from .crud import get_scheduler_health

    heartbeat = await get_scheduler_health()
    now = int(datetime.now(timezone.utc).timestamp())
    last = heartbeat.get("last_completed") or heartbeat.get("last_started") or 0
    scheduler_ok = now - last <= 180 and heartbeat.get("state") != "error"
    allowances = await get_allowances(get_wallet_id(wallet))
    overdue = sum(
        a.active and a.next_payment_date.timestamp() < now - 180 for a in allowances
    )
    pending = sum(bool(a.pending_payment_hash) for a in allowances)
    return {
        "healthy": scheduler_ok and not overdue and not pending,
        "scheduler_ok": scheduler_ok,
        "last_completed": heartbeat.get("last_completed"),
        "overdue": overdue,
        "pending": pending,
    }
