from http import HTTPStatus
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request
from lnbits.core.crud import get_user
from lnbits.decorators import require_admin_key, require_invoice_key

from .crud import (
    create_allowance,
    delete_allowance,
    get_allowance,
    get_allowances,
    update_allowance,
)
from .models import CreateAllowanceData, Allowance

allowance_api_router = APIRouter()

@allowance_api_router.get("/api/v1/allowance")
async def api_allowances(
    wallet=Depends(require_invoice_key),
) -> List[Allowance]:
    return await get_allowances([wallet.wallet.id])


@allowance_api_router.get("/api/v1/allowance/{allowance_id}")
async def api_allowance(
    allowance_id: str, wallet=Depends(require_invoice_key)
) -> Allowance:
    allowance = await get_allowance(allowance_id)
    if not allowance:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Allowance does not exist."
        )
    return allowance


@allowance_api_router.post("/api/v1/allowance", status_code=HTTPStatus.CREATED)
async def api_allowance_create(
    data: CreateAllowanceData, wallet=Depends(require_admin_key)
) -> Allowance:
    data.wallet = data.wallet or wallet.wallet.id
    return await create_allowance(data)


@allowance_api_router.put("/api/v1/allowance/{allowance_id}")
async def api_allowance_update(
    allowance_id: str, data: CreateAllowanceData, wallet=Depends(require_admin_key)
) -> Allowance:
    allowance = await get_allowance(allowance_id)
    if not allowance:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Allowance does not exist."
        )

    if allowance.wallet != wallet.wallet.id:
        raise HTTPException(
            status_code=HTTPStatus.FORBIDDEN, detail="Not your allowance."
        )

    data.id = allowance_id
    return await update_allowance(data)


@allowance_api_router.delete("/api/v1/allowance/{allowance_id}")
async def api_allowance_delete(
    allowance_id: str, wallet=Depends(require_admin_key)
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
    return {"message": "Allowance deleted"}