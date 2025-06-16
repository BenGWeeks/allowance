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
                       start_date, frequency_type, next_payment_date, memo, 
                       active, end_date
                FROM ext_allowance.maintable 
                ORDER BY start_date DESC
            """
            )
        else:
            # Filter by wallet ID
            rows = await conn.fetch(
                """
                SELECT id, name, wallet, lightning_address, amount, currency,
                       start_date, frequency_type, next_payment_date, memo, 
                       active, end_date
                FROM ext_allowance.maintable 
                WHERE wallet = $1
                ORDER BY start_date DESC
            """,
                wallet.id
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
                "start_date": (
                    row["start_date"].isoformat() if row["start_date"] else None
                ),
                "frequency_type": row["frequency_type"],
                "next_payment_date": (
                    row["next_payment_date"].isoformat()
                    if row["next_payment_date"]
                    else None
                ),
                "memo": row["memo"] or "",
                "active": row["active"],
                "end_date": row["end_date"].isoformat() if row["end_date"] else None,
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
                    if date_input.endswith('Z'):
                        date_input = date_input[:-1] + '+00:00'
                    # Parse ISO format and remove timezone
                    dt = datetime.fromisoformat(date_input)
                    return dt.replace(tzinfo=None)
                
                # If it's something else, try to convert to string first
                date_str = str(date_input)
                dt = datetime.fromisoformat(date_str)
                return dt.replace(tzinfo=None)
                
            except Exception as e:
                logger.warning(f"Error parsing datetime '{date_input}' (type: {type(date_input)}): {e}")
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
            allowance_id
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
        start_date = parse_datetime_string(data.start_date) if data.start_date else None
        next_payment_date = parse_datetime_string(data.next_payment_date) if data.next_payment_date else None
        end_date = parse_datetime_string(data.end_date) if data.end_date else None
        
        # Update the allowance
        await conn.execute(
            """
            UPDATE ext_allowance.maintable 
            SET name = $2, lightning_address = $3, amount = $4, currency = $5,
                start_date = $6, frequency_type = $7, next_payment_date = $8, 
                memo = $9, active = $10, end_date = $11
            WHERE id = $1
            """,
            allowance_id,
            data.name,
            data.lightning_address,
            data.amount,
            data.currency,
            start_date,
            data.frequency_type,
            next_payment_date,
            data.memo,
            data.active,
            end_date,
        )
        
        await conn.close()
        
        logger.info(f"✅ Updated allowance: {allowance_id}")
        return {"id": allowance_id, "name": data.name, "message": "Allowance updated successfully"}
        
    except HTTPException:
        # Re-raise HTTP exceptions (404, 403) as-is
        raise
    except Exception as e:
        logger.error(f"🚨 Database error in api_allowance_update: {e}")
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR, 
            detail=f"Failed to update allowance: {str(e)}"
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
                    if date_input.endswith('Z'):
                        date_input = date_input[:-1] + '+00:00'
                    # Parse ISO format and remove timezone
                    dt = datetime.fromisoformat(date_input)
                    return dt.replace(tzinfo=None)
                
                # If it's something else, try to convert to string first
                date_str = str(date_input)
                dt = datetime.fromisoformat(date_str)
                return dt.replace(tzinfo=None)
                
            except Exception as e:
                logger.warning(f"Error parsing datetime '{date_input}' (type: {type(date_input)}): {e}")
                return None
        
        start_date = parse_datetime_string(data.start_date) if data.start_date else None
        next_payment_date = parse_datetime_string(data.next_payment_date) if data.next_payment_date else None
        end_date = parse_datetime_string(data.end_date) if data.end_date else None
        
        # Connect to database
        conn = await asyncpg.connect(
            "postgresql://lnbits:password@allowance-postgres:5432/lnbits"
        )
        
        # Insert new allowance
        await conn.execute(
            """
            INSERT INTO ext_allowance.maintable 
            (id, name, wallet, lightning_address, amount, currency, start_date, 
             frequency_type, next_payment_date, memo, active, end_date)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
            """,
            data.id,
            data.name,
            wallet.id,
            data.lightning_address,
            data.amount,
            data.currency,
            start_date,
            data.frequency_type,
            next_payment_date,
            data.memo,
            data.active,
            end_date,
        )
        
        await conn.close()
        
        logger.info(f"✅ Created allowance: {data.id}")
        return {"id": data.id, "name": data.name, "message": "Allowance created successfully"}
        
    except Exception as e:
        logger.error(f"🚨 Error creating allowance: {e}")
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR, 
            detail=f"Failed to create allowance: {str(e)}"
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
            allowance_id
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
            allowance_id
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
            detail=f"Failed to delete allowance: {str(e)}"
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
