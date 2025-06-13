import json
from http import HTTPStatus

import httpx
from fastapi import Depends, Query, Request
from lnbits.core.crud import get_user
from lnbits.decorators import (
    check_admin,
    get_wallet_for_key,
    require_admin_key,
    require_invoice_key,
)
from loguru import logger
from starlette.exceptions import HTTPException

from . import allowance_ext
from .crud import (
    create_allowance,
    delete_allowance,
    get_allowance,
    get_allowances,
    update_allowance,
)
from .models import CreateAllowanceData


#######################################
##### ADD YOUR API ENDPOINTS HERE #####
#######################################

## Get all the records belonging to the user

@allowance_ext.get("/api/v1/allowance", status_code=HTTPStatus.OK)
async def api_allowances(
    all_wallets: bool = Query(False),
    wallet = Depends(require_invoice_key),
):
    wallet_ids = [wallet.wallet.id]
    if all_wallets:
        user = await get_user(wallet.wallet.user)
        wallet_ids = user.wallet_ids if user else []
    return [
        allowance.dict() for allowance in await get_allowances(wallet_ids)
    ]

## Get a single record

@allowance_ext.get("/api/v1/allowance/{allowance_id}", status_code=HTTPStatus.OK)
async def api_allowance(
    allowance_id: str, wallet = Depends(require_invoice_key)
):
    allowance = await get_allowance(allowance_id)
    if not allowance:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Allowance does not exist."
        )
    return allowance.dict()

## update a record

@allowance_ext.put("/api/v1/allowance/{allowance_id}")
async def api_allowance_update(
    data: CreateAllowanceData,
    allowance_id: str,
    wallet = Depends(require_admin_key),
):
    if not allowance_id:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Allowance does not exist."
        )
    allowance = await get_allowance(allowance_id)
    assert allowance, "Allowance couldn't be retrieved"

    if wallet.wallet.id != allowance.wallet:
        raise HTTPException(
            status_code=HTTPStatus.FORBIDDEN, detail="Not your allowance."
        )
    data.id = allowance_id
    allowance = await update_allowance(data)
    return allowance.dict()

## Create a new record

@allowance_ext.post("/api/v1/allowance", status_code=HTTPStatus.CREATED)
async def api_allowance_create(
    data: CreateAllowanceData,
    wallet = Depends(require_admin_key),
):
    data.wallet = data.wallet or wallet.wallet.id
    allowance = await create_allowance(data)
    return allowance.dict()

## Delete a record

@allowance_ext.delete("/api/v1/allowance/{allowance_id}")
async def api_allowance_delete(
    allowance_id: str, wallet = Depends(require_admin_key)
):
    allowance = await get_allowance(allowance_id)

    if not allowance:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Allowance does not exist."
        )

    if allowance.wallet != wallet.wallet.id:
        raise HTTPException(
            status_code=HTTPStatus.FORBIDDEN, detail="Not your allowance."
        )

    await delete_allowance(allowance_id)
    return "", HTTPStatus.NO_CONTENT